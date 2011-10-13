Date.prototype.format = function(format)
{
    var o =
    {
        "M+" : this.getMonth()+1, //month
        "d+" : this.getDate(),    //day
        "h+" : this.getHours(),   //hour
        "m+" : this.getMinutes(), //minute
        "s+" : this.getSeconds(), //second
        "q+" : Math.floor((this.getMonth()+3)/3),  //quarter
        "S" : this.getMilliseconds() //millisecond
    }
    if(/(y+)/.test(format))
    format=format.replace(RegExp.$1,(this.getFullYear()+"").substr(4 - RegExp.$1.length));
    for(var k in o)
    if(new RegExp("("+ k +")").test(format))
    format = format.replace(RegExp.$1,RegExp.$1.length==1 ? o[k] : ("00"+ o[k]).substr((""+ o[k]).length));
    return format;
}

var App = {
  Models: {},
  Views: {},
  Routers: {},
  RestUrl: '/ajax',
  Router: {},
  initialize: function(Router) {
    this.Router = new Router;
    Backbone.history.start();
  }
};

App.Models.Report = Backbone.Model.extend({
  defaults: {
    site_id: '',
    report_type: 'pu',
    report_date: '30',
    report_from_date: '',
    report_to_date: '',
    data: {},
    code: '' 
  },
  url: function() {
    return "http://127.0.0.1:4000/ajax/get_site_statistics?site_id=kuaishubao&from_date_str=" + this.get('report_from_date').format('yyyy-MM-dd') + "&to_date_str=" + this.get('report_to_date').format('yyyy-MM-dd');
    //return App.RestUrl + '/report/' + this.get('site_id') + '/' + this.get('report_type') + '/' + this.get('report_date_range');
  },
  initialize: function() {
    this.set({site_id: $('#site_id').val()});
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
 
App.Views.Report = Backbone.View.extend({
  model: {},
  initialize: function() {
    _.bindAll(this,'renderSidebarNav','renderContent','renderChart');
    this.model.bind('change:data',this.renderChart);

    this.renderSidebarNav();
    this.renderContent();
    //this.renderChart();
  },

  renderSidebarNav: function() {
    var v = {
      report_type: this.model.get('report_type'), 
      report_date: this.model.get('report_date')
    };
    var template = _.template($('#sidebar_nav_template').html() ,v);
    $('#sidebar_nav').html(template);
    return this;
  },

  renderContent: function() {
    var report_type = this.model.get('report_type');
    var report_date = this.model.get('report_date');
    var from_day = this.model.get('report_from_date');
    var to_day = this.model.get('report_to_date');
    var v = {
      report_type: report_type,
      links: [15,30,60,90],
      primary_day: report_date,
    };
    var template = _.template( $('#content_template').html(), v);
    $('#content').html(template);
    $('#report_nav').text($('#report-link-' + this.model.get('report_type')).text());

    $('#widgetCalendar').DatePicker({
      date: new Date(),
    });
    var date_range_split_str = ' -- ';
    $('#widgetRangeText').text(from_day.format('yyyy-MM-dd') + date_range_split_str + to_day.format('yyyy-MM-dd'));

    var current_month = new Date(to_day);
    current_month.addMonths(-1);

    var min_from_day = new Date();
    min_from_day.addDays(-100);
    var max_to_day = new Date();
    max_to_day.addDays(-1);
    
    $('#widgetCalendar').DatePicker({
      flat: true,
      date: [from_day, to_day],
      calendars: 3,
      current: current_month,
      mode: 'range',
      starts: 1,
      locale: {
        days: ["日", "一", "二", "三", "四", "五", "六", "日"],
        daysShort: ["日", "一", "二", "三", "四", "五", "六", "日"],
        daysMin: ["日", "一", "二", "三", "四", "五", "六", "日"],
        months: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
        monthsShort: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
        weekMin: '周'
      },
      onChange: function(formated) {
        $('#widgetCalendarRangeText').text(formated.join(date_range_split_str));
      },
      onRender: function(date) {
        return {
          disabled: (date.valueOf() > max_to_day.valueOf() || date.valueOf() < min_from_day.valueOf())
        }
      }
    });
    var state = false;
    var calendar_state_toggle = function() {
      $('#widgetCalendar').stop().animate({height: state ? 0 : $('#widgetCalendar div.datepicker').get(0).offsetHeight}, 200);
      $('#chart').stop().animate({'padding-top': state ? 0 : $('#widgetCalendar div.datepicker').get(0).offsetHeight}, 200);
      //state ? $('#quickSelectRange a').removeClass('disabled') :  $('#quickSelectRange a').addClass('disabled');
      state = !state;
    };

    $('#confirm_range').bind('click', function(){
      calendar_state_toggle();
      $('#widgetRangeText').text($('#widgetCalendarRangeText').text());
      var temp = $('#widgetCalendar').DatePickerGetDate();
      from_day = temp[0];
      to_day = temp[1];
      App.Router.navigate($('#report_type').val() + '/' + from_day.format('yyyy-MM-dd') + '--' + to_day.format('yyyy-MM-dd'), true);
      return false;
    });

    $('#cancel_range').bind('click', function(){
      calendar_state_toggle();
      return false;
    });


    $('#widgetField').bind('click', function(){
      calendar_state_toggle();
      if(state == true) {
        $('#widgetCalendarRangeText').text($('#widgetRangeText').text());
        $('#widgetCalendar').DatePickerSetDate([from_day, to_day]);
      }
      return false;
    });

      return this;
  },

  renderChart: function() {
    var data = this.model.get('data');
    var chart_dict = {
      chart: {
        renderTo: "chart-container"
      },
      title: {
        text: "商品PV和UV图"
      },
      xAxis: {
        categories: data.site.statistics.categories,
      },
      yAxis: [{
        title: {
          text: '次数'
        }
      },{
        title: {
          text: '比率'
        },
        opposite: true
      }],

      tooltip: {
        formatter: function() {
          return '<b>' + this.series.name + '</b><br/>' +
          this.x + ':' + this.y + '次';
        }
      },

      series: [{
        "name": "商品PV",
        "data": data.site.statistics.pv_v,
        "type": "area"
      },{
        "name": "商品UV",
        "data": data.site.statistics.uv_v,
        "type": "area",
      },{
        "name": "PV/UV",
        "data": data.site.statistics.pv_uv,
        "type": "line",
        yAxis: 1
      }]
    };
   
    var chart_temp = new App.Models.DayChart({chart_dict: chart_dict});

    return this;
  }
});

App.Routers.Report = Backbone.Router.extend({
  routes: {
      ":report_type": "getPost",
      ":report_type/:report_date": "getPost",
  },
  getPost: function(report_type, report_date) {
    var r = new App.Models.Report;
    if(typeof(report_type) !== 'undefined' && report_type !== '') r.set({'report_type': report_type});
    if(typeof(report_date) !== 'undefined' && report_date !== '') r.set({'report_date': report_date});
    $('#report_type').val(r.get('report_type'));
    var report_view = new App.Views.Report({model: r});
    r.fetch({
      success: function(model,response){
        r.set({data:response});
      }
    });
  },
  defaultRoute: function( actions ){
    alert('Error');
  }
});

function x_add_weekend_shadow(c)
{
    var left;
    var xcount = xAxisLabels.length; 
    $(xAxisLabels).each(function(i, label){
        var c_date = label.split("-");
        var d  =  new Date(c_date[0], c_date[1]-1, c_date[2]);
        var week = d.getUTCDay();
        if(week == 5 || week == 6)
        {
            width = c.xAxis[0].translate(2) - c.xAxis[0].translate(1)
            left = Math.round(i * width + c.plotLeft+1)
            if(left < c.plotLeft + c.plotWidth)
            {
                c.renderer.rect(left, c.plotTop, width, c.plotHeight,0).attr({
                    'stroke-width': 0,
                    stroke: '#000',
                    fill: '#ddd',
                    zIndex: -1,
                    'label': c_date,
                    'left': i * width + c.plotLeft,
                    'class': 'rec_weekend_shadow'
                }).add();
            }
        }
    });
}

$(document).ready(function(){
Highcharts.theme = {
   chart: {
      margin: [50, 80, 60, 45],
      events: {
//       redraw: function() {
//          $(".rec_weekend_shadow").remove();
//          x_add_weekend_shadow(this);
//       }
      }
   },
   
   //colors: ['#005BC8', '#54B428', '#B7461C', '#FF9655', '#54B428', '#64E572', '#FF9655', '#FFF263', '#6AF9C4'],
//   colors: ['#058DC7', '#50b432', '#ed7e17', '#FF9655', '#50b432', '#64E572', '#FF9655', '#FFF263', '#6AF9C4'],
//   colors: ["#7798BF", "#55BF3B", "#DF5353", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#7798BF", "#aaeeee"],
 
   credits: {
      href: "http://tuijianbao.net",
      text: "",
      style: {
           color: '#ccc'
      }
   },

   labels: {
      style: {
         //color: '#99b'
      }
   },
   legend: {
         align: 'left',
         verticalAlign: 'top',
         y: 10,
         x: 40,
         floating: true,
         borderWidth: 0,

      itemStyle: {         
         font: '9pt Trebuchet MS, Verdana, sans-serif',
         //color: 'black'

      },
      itemHoverStyle: {
         //color: '#039'
      },
      itemHiddenStyle: {
         //color: 'gray'
      }
   },
   plotOptions: {
      area: {
         fillOpacity: .20,
         lineWidth: 3 
      },
      areaspline: {
         marker: {
            enabled: false,
            symbol: 'circle',
            radius: 2,
            states: {
               hover: {
                  enabled: true
               }
            }
         }
      },
      column: {
        borderWidth: 1,
        groupPadding: 0
      },
      line: {
        //lineWidth: 1
      }
   },
   subtitle: {
      x: -20,
      style: { 
         //color: '#666666',
         font: 'bold 12px "Trebuchet MS", Verdana, sans-serif'
      }
   },
   title: {
      x: -20,
      style: { 
         //color: '#000',
         font: 'bold 16px "Trebuchet MS", Verdana, sans-serif'
      }
   },

   xAxis: {
      //gridLineWidth: 1,
      //lineColor: '#000',
      //tickColor: '#000',
      labels: {
         rotation: -45,
         style: {
            //color: '#000',
            font: '11px Trebuchet MS, Verdana, sans-serif'
         },
      },
      title: {
         style: {
            //color: '#333',
            fontWeight: 'bold',
            fontSize: '12px',
            fontFamily: 'Trebuchet MS, Verdana, sans-serif'

         }            
      }
   },
   yAxis: {
      //minorTickInterval: 'auto',
      //lineColor: '#000',
      //lineWidth: 1,
      tickWidth: 1,
      //tickColor: '#000',
      labels: {
         style: {
            //color: '#000',
            font: '11px Trebuchet MS, Verdana, sans-serif'
         }
      },
      title: {
         style: {
            //color: '#333',
            fontWeight: 'bold',
            fontSize: '12px',
            fontFamily: 'Trebuchet MS, Verdana, sans-serif'
         }            
      }
   }
 };
 
var highchartsOptions = Highcharts.setOptions(Highcharts.theme);
App.initialize(App.Routers.Report);

})
