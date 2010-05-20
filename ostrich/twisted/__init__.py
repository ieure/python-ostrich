import json

from twisted.web import static
from twisted.web.resource import Resource

from ostrich import stats
from ostrich.time_series_collector import TimeSeriesCollector

class StatsResource(Resource):
    def render_GET(self, request):
        reset = int(request.args.get('reset', [0])[0])
        return json.dumps(stats.stats(reset=reset), default=stats.json_encoder)

class StatsTimeSeriesResource(StatsResource):
    def __init__(self):
        Resource.__init__(self)
        self.collector = TimeSeriesCollector()
        self.collector.start_twisted()
        
        self.putChild('', StatsResource())
        self.putChild('graph', static.Data(GRAPH_HTML.strip(), "text/html"))
        self.putChild('graph_data', TimeSeriesDataResource(self.collector))
    
    # def render_GET(self, request):
    #     reset = int(request.args.get('reset', [0])[0])
    #     return json.dumps(stats.stats(reset=reset), default=stats.json_encoder)

class TimeSeriesDataResource(Resource):
    isLeaf = True
    
    def __init__(self, collector):
        self.collector = collector
    
    def render_GET(self, request):
        if len(request.postpath) == 0:
            return json.dumps({'keys': self.collector.keys()}) + "\n"
        else:
            return json.dumps(self.collector.get(request.postpath[0])) + "\n"


GRAPH_HTML = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
  <script type="text/javascript" src="http://www.google.com/jsapi"></script>
  <script type="text/javascript" src="http://danvk.org/dygraphs/dygraph-combined.js"></script>
  <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.4.1/jquery.min.js"></script>
  <script type="text/javascript">
    if (document.location.search.length > 0) {
      google.load('visualization', '1');
      google.setOnLoadCallback(drawChart);
    } else {
      $.getJSON("graph_data", function(datadump) {
        var keys = datadump["keys"].sort();
        for (i in keys) {
          $("#contents").append('<a href="graph.html?' + keys[i] + '">' + keys[i] + '</a><br/>');
        }
        $("#graph-container").css("display", "none");
      });
    }
    
    function roundTo(number, digits) {
      return Math.round(number * Math.pow(10, digits)) / Math.pow(10, digits);
    }

    function drawChart() {
      var key = document.location.search.substr(1);
      if (key.substr(0, 7) == "timing:") {
        drawChartOf(key, 6);
      } else {
        drawChartOf(key, 1);
      }
    }

    function drawChartOf(key, columns) {
      $.getJSON("graph_data/" + key, function(datadump) {
        var rawData = datadump[key];
        var data = new google.visualization.DataTable();
        data.addColumn('datetime', 'Time');
        for (i = 0; i < columns; i++) {
          data.addColumn('number', 'Data' + i);
        }
        data.addRows(rawData.map(function(row) { return [ new Date(row[0] * 1000) ].concat(row.slice(1)); }));

        new Dygraph.GVizChart(document.getElementById('chart')).draw(data, {
          includeZero: true,
          fillGraph: true,
          labelsKMG2: true,
          xAxisLabelFormatter: function(date, granularity) { return date.strftime("%H:%M"); },
          labelsDivStyles: { display: "none" },
          highlightCallback: function(e, x, pts) {
            var label = document.getElementById('chart_label');
            $('#chart_label').html(roundTo(pts[0].yval, 3));
            $('#chart_label').css({ display: "block", left: (Math.floor(pts[0].canvasx) + 15) + "px", top: (Math.floor(pts[0].canvasy) + 15) + "px" });
          },
          unhighlightCallback: function(e) {
            $('#chart_label').css({ display: "none" });
          },
        });
      });
    }
  </script>
</head>
<body>

<div id="graph-container">
<div id="chart" style="width: 400px; height: 200px;"></div>
<span id="chart_label" style="position: absolute;"></span>
</div>
<div id="contents"></div>

</body>
</html>
"""