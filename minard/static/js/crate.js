function createArray(length) {
    var arr = new Array(length || 0),
        i = length;

    if (arguments.length > 1) {
        var args = Array.prototype.slice.call(arguments, 1);
        while(i--) arr[length-1 - i] = createArray.apply(this, args);
    }

    return arr;
}

var crate_setup = createArray(19,32,16);

for (var i=0; i < 19; i++) {
    for (var j=0; j < 32; j++) {
        for (var k=0; k < 16; k++) {
            crate_setup[i][j][k] = (i << 16) | (k << 8) | j;
        }
    }
}


function crate_view() {
    var margin = {top: 20, right: 25, bottom: 50, left: 25},
        width = null,
        height = null;

    var threshold = null;

    var svg;

    var click = function(d, i) { return; };

    function chart(selection) {
        selection.each(function(data) {
        if (width === null)
            width = $(this).width() - margin.left - margin.right;

        if (height === null)
            height = Math.round(width/1.6) - margin.top - margin.bottom;

        var root = d3.select(this).selectAll('table').data([1]);

        var table = root.enter().append('table')
            .attr('style','font-size:4pt;border-collapse:separate;border-spacing:1px')
          .append('tr');

        var tr1 = table.selectAll('td')
            .data(crate_setup)
            .enter().append('td').append('table')
            .attr('style','padding:2px;border-collapse:separate;border-spacing:1px');

        var tr2 = tr1.selectAll('tr')
            .data(function(d) { return d; })
            .enter().append('tr');

        var td = tr2.selectAll('td')
            .data(function(d) { return d; }, function(d) { return d; })
            .enter().append('td')
            .attr('style','background-color:gray');

        var k = [],
            v = [];

        for (var key in data) {
            k.push(key);
            v.push(data[key]);
        }

        var select = d3.select(this).selectAll('table tr td table tr td')
            .data(k, function(d) { return d; });

        select.attr('style', function(d, i) {
            return (v[i] > threshold) ? 'background-color:red' : 'background-color:black';
            });

        select.exit().attr('style','background-color:gray');
       });}

       chart.height = function(value) {
           if (!arguments.length) return height;
           height = value;
           return chart;
       }

       chart.width = function(value) {
           if (!arguments.length) return width;
           width = value;
           return chart;
       }

       chart.click = function(value) {
           if (!arguments.length) return click;
           click = value;
           return chart;
       }

       chart.threshold = function(value) {
           if (!arguments.length) return threshold;
           threshold = value;
           return chart;
       }

    return chart;
}