# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import time
import subprocess

from django.http import Http404, HttpResponse, HttpResponseRedirect

from django.template import RequestContext
from django.shortcuts import render_to_response

try:
    from django.http import StreamingHttpResponse
except ImportError:
    # if we get here we are on older django so this app shouldn't
    # even be visible - this will silence code error checkers though
    from django.http import HttpResponse as StreamingHttpResponse

from rvbd_common.apps.console.models import Utility, Results, Parameter
from rvbd_common.apps.console.forms import ( UtilityDetailForm, ParameterStringForm,
                                             get_utility_formset)

from project.settings import PROJECT_ROOT, LOGGING, DEBUG

# monkeypatch to address Python Bug #14308: http://bugs.python.org/issue14308
# affects subprocess function in execute method
#
import threading
threading._DummyThread._Thread__stop = lambda x: 42

SCRIPT_DIR = os.path.join(PROJECT_ROOT,'apps', 'console', 'scripts')


def main(request):
    """ Provide list of installed scripts
    """
    logfiles = Utility.objects.filter(islogfile=True).select_related()
    utilities = Utility.objects.filter(islogfile=False).select_related()
    results = [u.results_set.all().order_by('-run_date') for u in utilities]

    utility_list = []
    for u, r in zip(utilities, results):
        if r:
            utility_list.append((u, r[0].run_date, len(r)))
        else:
            utility_list.append((u, '--', len(r)))

    return render_to_response('main.html',
                              {'utilities': utility_list,
                               'logfiles': logfiles},
                              context_instance=RequestContext(request))


def refresh(request):
    """ Re-populate Utility store based on contents of scripts folder
    """
    ignores = [lambda x:x.endswith('.swp'),
               lambda x:x.endswith('~'),
               lambda x:x.endswith('.bak'),
               lambda x:x.startswith('.'),
               ]

    utilities = [u.name for u in Utility.objects.all()]
    files = os.listdir(SCRIPT_DIR)
    files = [x for x in files if not any(c(x) for c in ignores)]

    # get scripts
    for f in files:
        if f not in utilities:
            Utility(name=f, path=SCRIPT_DIR).save()

    # get logfiles - but only if debug is turned on
    if DEBUG:
        for handler, values in LOGGING['handlers'].iteritems():
            try:
                path, f = os.path.split(values['filename'])
                if f not in utilities:
                    Utility(name=f, path=path, islogfile=True).save()
            except KeyError:
                pass

    return HttpResponseRedirect('/console')


def detail(request, script_id):
    """ Return details about specific script
    """
    ParameterFormSet = get_utility_formset()

    try:
        utility = Utility.objects.get(pk=script_id)
    except:
        raise Http404

    if request.method == 'POST':
        form = UtilityDetailForm(request.POST, instance=utility)
        formset = ParameterFormSet(request.POST, instance=utility)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        form = UtilityDetailForm(instance=utility)
        formset = ParameterFormSet(instance=utility)

    return render_to_response('detail.html',
                              {'utility': utility,
                               'form': form,
                               'formset': formset},
                              context_instance=RequestContext(request))


def run(request, script_id):
    """ Execute utility script
    """
    try:
        utility = Utility.objects.get(pk=script_id)
    except:
        raise Http404

    last_runs = Results.objects.filter(utility=utility).order_by('-run_date')
    if last_runs and last_runs[0].parameters:
        parameter_string = last_runs[0].parameters
    else:
        parameter_string = Parameter.objects.get_param_string(utility)

    if request.method == 'POST':
        form = UtilityDetailForm(request.POST, instance=utility)
        parameters = ParameterStringForm(request.POST)
        if form.is_valid():
            return StreamingHttpResponse(execute(utility, form, parameters))
        else:
            return HttpResponse('Error Processing Form.')
    else:
        form = UtilityDetailForm(instance=utility)
        parameters = ParameterStringForm(initial={'parameter_string': parameter_string})

    return render_to_response('run.html',
                              {'utility': utility,
                               'form': form,
                               'parameters': parameters},
                              context_instance=RequestContext(request))


def execute(utility, form, params_form):
    """ Executes the given utility, streaming stdout in the response

        Any report on stderr will prompt an attempt to generate
        help data for further information.
    """
    res = []
    path = os.path.join(SCRIPT_DIR, utility.name)
    #print 'path: %s' % path

    if not utility.islogfile:
        if params_form.is_valid():
            parameters = params_form.cleaned_data['parameter_string']
            cmd = '%s %s' % (path, parameters)
            cmd = cmd.split()
        else:
            parameters = ''
            cmd = path

        print 'cmd: %s' % cmd

        env = dict(os.environ)
        env['PYTHONUNBUFFERED'] = 'True'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            line = p.stdout.readline()
            while line:
                res.append(line)
                # force browser buffer to flush with spaces
                #yield '{} <br> {}'.format(line, ' '*1024)
                yield '{}'.format(line)
                line = p.stdout.readline()
            p.stdout.close()

            errflag = False
            err = p.stderr.readline()
            while err:
                res.append(err)
                yield '{} <br> {}'.format(err, ' ')
                errflag = True
                err = p.stderr.readline()
            p.stderr.close()
        finally:
            # if we leave the page this should clean up and kill the process
            p.stdout.close()
            p.stderr.close()
            p.terminate()
            Results(utility=utility, parameters=parameters, results=res).save()

        if errflag:
            # rerun with help command to show additional info
            p = subprocess.Popen([path, '--help'], stdout=subprocess.PIPE)
            line = p.stdout.readline()
            while line:
                res.append(line)
                # force browser buffer to flush with spaces
                #yield '{} <br> {}'.format(line, ' '*1024)
                yield '{}'.format(line)
                line = p.stdout.readline()
            p.stdout.close()
    else:
        log = os.path.join(utility.path, utility.name)

        # scan near the end of the log first
        # TODO make this configurable
        avg_line_length = 80
        lines = 30

        with open(log, 'r') as f:
            try:
                f.seek(-lines*avg_line_length, 2)
                f.readline()
            except IOError:
                # seeked too far?
                f.seek(0)

            while 1:
                where = f.tell()
                line = f.readline()
                if not line:
                    time.sleep(3)
                    f.seek(where)
                else:
                    yield line


def status(request, script_id):
    """ Return status of installed script
    """
    pass

