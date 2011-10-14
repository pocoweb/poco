App.Models.Report = Backbone.Model.extend({
  defaults: {
    api_key: '',
    report_type: 'pv_uv',
    report_date: '30',
    report_from_date: '',
    report_to_date: '',
    data: {},
    code: '' 
  },
  url: function() {
    return App.RestUrl + '/report?api_key=' + this.get('api_key') + '&report_type=' + this.get('report_type')
    + '&from_date=' + this.get('report_from_date').format('yyyy-MM-dd') + '&to_date=' + this.get('report_to_date').format('yyyy-MM-dd');
  },
  initialize: function() {
    this.set({api_key: $('#api_key').val()});
    this.bind('change:report_date', this.setReportDateRange);
    this.setReportDateRange();
  },
  setReportDateRange: function() {
    report_date = this.get('report_date');
    var date_range_array = report_date.split('--');
    if ( date_range_array.length == 1)
    {
      var from_day = new Date();
      var to_day = new Date();
      from_day.setDate(to_day.getDate()-report_date-1);
      to_day.setDate(to_day.getDate()-1);
    }
    else if ( date_range_array.length == 2)
    {
      var from_day_array = date_range_array[0].split('-');
      var to_day_array = date_range_array[1].split('-');
      var from_day = new Date(from_day_array[0],from_day_array[1]-1,from_day_array[2]);
      var to_day = new Date(to_day_array[0],to_day_array[1]-1,to_day_array[2]);
    }
    else
    {
      alert('error');
    }
    this.set({report_from_date: from_day, report_to_date: to_day});
    return this;
  }
});

App.Models.DayChart = Backbone.Model.extend({
  defaults: {
    renderTo: 'chart-container',
    title: '',
    chart_dict: {},
    weekend_shadow: true,
    xAxisLabels: [],
  },
  initialize: function() {
    var model = this;
    (model.get('chart_dict')).chart.events = {redraw:  model.redraw(model)};
    (model.get('chart_dict')).xAxis.labels = model.labels(model);
    var chart = new Highcharts.Chart(model.get('chart_dict'), function(c){model.x_add_weekend_shadow(model,c)});
  },

  redraw: function(model){
    return function(){
      $(".rec_weekend_shadow").remove();
      model.x_add_weekend_shadow(model,this);
    }
  },

  labels : function(model){
    return  {
      x: -5,
      y: 18,
      formatter: function(){
        model.get('xAxisLabels').push(this.value);
        var c_date = this.value.split("-");
        var d  =  new Date(c_date[0], c_date[1]-1, c_date[2]);
        var week = d.getUTCDay();
        if(week == 0)
        {
           return "" + c_date[1] + "-" + c_date[2]
        }
        else
        {
           return ""
        }
      }
    }
  },
  
  x_add_weekend_shadow: function(model, c){
    var left;
    var xcount = model.get('xAxisLabels').length; 
    var width = c.xAxis[0].translate(2) - c.xAxis[0].translate(1);
    var last_left = 0;
    $(model.get('xAxisLabels')).each(function(i, label){
      var c_date = label.split("-");
      var d  =  new Date(c_date[0], c_date[1]-1, c_date[2]);
      var week = d.getUTCDay();
      if(week == 5 || week == 6)
      {
        if(week == 5)
        {
          left = Math.round(i * width + c.plotLeft+1);
          last_left = left;
        }
        else
        {
          left = last_left + width;
        }
        if(left < c.plotLeft + c.plotWidth)
        {
           c.renderer.rect(left, c.plotTop, width, c.plotHeight,0).attr({
           'stroke-width': 0,
           stroke: '#333',
           fill: '#eee',
           zIndex: -1,
           'label': c_date,
           'left': i * width + c.plotLeft,
           'class': 'rec_weekend_shadow',
           }).add();
         }
        }
      });
  }
});
