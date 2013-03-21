# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import subprocess

from django.http import Http404, HttpResponse, StreamingHttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.shortcuts import render_to_response

from apps.console.models import Utility, Results, Parameter, Job
from apps.console.forms import ExecuteForm

from project.settings import PROJECT_ROOT

SCRIPT_DIR = os.path.join(PROJECT_ROOT,'apps', 'console', 'scripts')

def main(request):
    """ Provide list of installed scripts
    """
    utilities = Utility.objects.all().select_related()
    return render_to_response('main.html',
                              {'utilities': utilities},
                              context_instance=RequestContext(request))


def reload(request):
    """ Re-populate Utility store based on contents of scripts folder
    """
    utilities = [u.name for u in Utility.objects.all()]
    files = os.listdir(SCRIPT_DIR)

    for f in files:
        if f not in utilities:
            Utility(name=f, path=SCRIPT_DIR).save()
    return HttpResponseRedirect('/console')


def detail(request, script_id):
    """ Return details about specific script
    """
    try:
        utility = Utility.objects.get(pk=script_id)
    except:
        raise Http404
    return render_to_response('detail.html',
                              {'utility': utility},
                              context_instance=RequestContext(request))


def run(request, script_id):
    """ Execute utility script
    """
    try:
        utility = Utility.objects.get(pk=script_id)
    except:
        raise Http404

    if request.method == 'POST':
        form = ExecuteForm(request.POST, instance=utility)
        if form.is_valid():
            return StreamingHttpResponse(execute(utility, form))
        else:
            return HttpResponse('Error Processing Form.')
    else:
        form = ExecuteForm(instance=utility)

    return render_to_response('run.html',
                              {'utility': utility,
                               'executeForm': form},
                              context_instance=RequestContext(request))


def execute(utility, form):
    res = []
    path = os.path.join(SCRIPT_DIR, utility.name)
    print path

    p = subprocess.Popen(path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    line = p.stdout.readline()
    while line:
        res.append(line)
        print line
        # force browser buffer to flush with spaces
        #yield '{} <br> {}'.format(line, ' '*1024)
        yield '{} <br> {}'.format(line, ' ')
        line = p.stdout.readline()
    p.stdout.close()

    for line in iter(p.stderr.readline, ''):
        res.append(line)
        yield line + "<br>"
    p.stderr.close()
    Results(utility=utility, results=res).save()

def status(request, script_id):
    """ Return status of installed script
    """
    pass


def upload(request):
    """ Upload new scripts
    """
    pass
