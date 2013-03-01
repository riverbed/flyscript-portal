<!DOCTYPE html>
<html>
  <head>
    <title> {{ report.title }}</title>
    <link href="{{ STATIC_URL }}css/bootstrap.min.css" rel="stylesheet" media="screen"/>
    <link href="{{ STATIC_URL }}css/bootstrap.min.css" rel="stylesheet" media="print"/>
    <link href="{{ STATIC_URL }}css/main.css" rel="stylesheet"/>
    <link href="{{ STATIC_URL }}css/showLoading.css" rel="stylesheet"/>

    <script type="text/javascript" src="{{ STATIC_URL }}js/jquery-latest.js"></script>
    <script type="text/javascript" src="{{ STATIC_URL }}js/jquery.showLoading.js"></script>
    <script type="text/javascript" src="{{ STATIC_URL }}js/yui3/yui/yui-min.js"></script>
    <script type="text/javascript" src="{{ STATIC_URL }}js/bootstrap.min.js"></script>
    <script type="text/javascript" src="{{ STATIC_URL }}js/widgets.js"></script>

    <script type="text/javascript">
      $(document).ready( function() {
          {% autoescape off %} 
          {% for row in rows %}
            {% for w in row %}
            new {{ w.widgettype }} 
              ( "/report/{{ report.id }}/data/{{ w.id }}", 
                "chart_{{ w.row }}_{{ w.col }}", 
                {{ w.options }} );
            {% endfor %}
          {% endfor %}
          {% endautoescape %} 
        });

    </script>

  </head>
  <body>
    <div class="navbar navbar-inverse navbar-fixed-top">
      <div class="navbar-inner">
        <div class="container">
          <a class="btn btn-navbar" data-toggle="collapse" data-target=".nav-collapse">
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </a>
          <a class="brand" href="http://www.riverbed.com"> Riverbed </a>
          <div class="nav-collapse collapse">
            <ul class="nav">
              <li class="dropdown active">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown"> {{ report.title }} <b class="caret"></b></a>
                <ul class="dropdown-menu">
                  {% for d in reports %}
                  <li><a href="/report/{{ d.id }}">{{ d.title }}</a></li>
                  {% endfor %}
                </ul>
              </li>
            </ul>
          </div><!--/.nav-collapse -->
        </div>
      </div>
    </div>
    <div class="container-fluid">
      {% for row in rows %}
        <div class="row">
          {% for w in row %}
            <div class="span{{ w.colwidth }}" id="chart_{{ w.row }}_{{ w.col }}">chart_{{ w.row }}_{{ w.col }}</div>
          {% endfor %}
        </div>
      {% endfor %}
    </div>
  </body>
</html>

