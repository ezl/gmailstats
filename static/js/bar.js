function renderBarGraph(data, elementId, containerWidth) {

// var barWidth = 40;
// var width = (barWidth + 10) * data.length;
var height = 200;

var width = containerWidth;
var barWidth = (containerWidth - 20 - 10 * data.length) / data.length;

var x = d3.scale.linear().domain([0, data.length]).range([0, width]);
var y = d3.scale.linear().domain([0, d3.max(data, function(datum) { return datum.count; })]).
  rangeRound([0, height]);

// add the canvas to the DOM
var barDemo = d3.select(elementId).
  append("svg:svg").
  attr("width", width).
  attr("height", height);

barDemo.selectAll("rect").
  data(data).
  enter().
  append("svg:rect").
  attr("x", function(datum, index) { return x(index); }).
  attr("y", function(datum) { return height - y(datum.count); }).
  attr("height", function(datum) { return y(datum.count); }).
  attr("width", barWidth).
  attr("fill", "#2d578b");

barDemo.selectAll("text").
  data(data).
  enter().
  append("svg:text").
  attr("x", function(datum, index) { return x(index) + barWidth; }).
  attr("y", function(datum) { return height - y(datum.count); }).
  attr("dx", -barWidth/2).
  attr("dy", "1.2em").
  attr("text-anchor", "middle").
  text(function(datum) { return datum.count;}).
  attr("fill", "white");

barDemo.append("svg")
  .style("height", 100);

barDemo.selectAll("text.yAxis").
  data(data).
  enter().append("svg:text").
  attr("x", function(datum, index) { return x(index) + barWidth; }).
  attr("y", height).
  attr("dx", -barWidth/2).
  attr("text-anchor", "middle").
  attr("style", "font-size: 12; font-family: Helvetica, sans-serif").
  text(function(datum) { return datum.date;}).
  attr("transform", "translate(0, 18)").
  attr("class", "yAxis");

}
