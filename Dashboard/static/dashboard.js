var App = {
  Models: {},
  Views: {},
  Controllers: {},
  RestUrl: '/ajax',
  initialize: function() {
    new App.Controllers.Routes();
    Backbone.history.start();
  }
};

App.Models.Stat = Backbone.Model.extend({
  defaults: {
    site_id: '',
    type: '',
    date: 30,
    code: '' 
  },
  url: function() {
    var url = App.RestUrl + '/stat/';
    return App.RestUrl + '/stat/' + this.get('site_id') + '/' + this.get('type') + '/' + this.get('date');
  }
});

App.Views.Stat = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'render');
    this.model.bind("change", this.render);
  },

  render: function() {
    console.log(this.model.get('site_id'));
    console.log(this.model.get('type'));
    return this;
  }
});

App.Controllers.Routes = Backbone.Router.extend({
  routes: {
      "stat/:site_id/:stat_type": "getPost",
      "stat/:site_id/:stat_type/:days_ago": "getPost",
      "stat/:site_id/:stat_type/:from/:to": "getPost",
      "*actions": "defaultRoute" // Backbone will try match the route above first
  },
  getPost: function( id, type ) {
    var a = new App.Models.Stat;
    a.set({site_id: id, type: type});
    $.getJSON(a.url(), function(data) {
      var vxxx = new App.Views.Stat({model: a});
      a.set(data);
    });
  },
  defaultRoute: function( actions ){
      //alert( actions ); 
  }
});

App.initialize();

// Instantiate the router
// Start Backbone history a neccesary step for bookmarkable URL's

$(document).ready(function(){
  $('#widgetCalendar').DatePicker({
    date: new Date(),
  });
  
  var date_range_split_str = " -- ";
  var date_range_array =  $('#widgetRangeText').text().split(date_range_split_str);
  var from_day_array = date_range_array[0].split('-');
  var to_day_array = date_range_array[1].split('-');
  var from_day = new Date(from_day_array[0],from_day_array[1]-1,from_day_array[2]);
  var to_day = new Date(to_day_array[0],to_day_array[1]-1,to_day_array[2]);

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
    $('#widgetCalendar').stop().animate({height: state ? 0 : $('#widgetCalendar div.datepicker').get(0).offsetHeight+30}, 200);
    $('#chart').stop().animate({'padding-top': state ? 0 : $('#widgetCalendar div.datepicker').get(0).offsetHeight+30}, 200);
    state ? $('#quickSelectRange a').removeClass('disabled') :  $('#quickSelectRange a').addClass('disabled');
    state = !state;
  };

  $('#confirm_range').bind('click', function(){
    calendar_state_toggle();
    $('#widgetRangeText').text($('#widgetCalendarRangeText').text());
    var temp = $('#widgetCalendar').DatePickerGetDate();
    from_day = temp[0];
    to_day = temp[1];
    app_router.navigate("stat/fdd/dfs",true);
    return false;
  });

  $('#cancel_range').bind('click', function(){
    calendar_state_toggle();
    return false;
  });


  $('#widgetField>a').bind('click', function(){
    calendar_state_toggle();
    if(state == true) {
      $('#widgetCalendarRangeText').text($('#widgetRangeText').text());
      $('#widgetCalendar').DatePickerSetDate([from_day, to_day]);
    }
    return false;
  });

  var chart = new Highcharts.Chart({
    chart: {
      renderTo: 'chart-container',
      defaultSeriesType: 'line',
      marginRight: 130,
      marginBottom: 25
    },
    title: {
      text: 'Monthly Average Temperature',
      x: -20 //center
    },
    subtitle: {
      text: 'Source: WorldClimate.com',
      x: -20
    },
    xAxis: {
      categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      },
      yAxis: {
        title: {
          text: 'Temperature (Â°C)'
        },
        plotLines: [{
          value: 0,
          width: 1,
          color: '#808080'
        }]
        },
        tooltip: {
          formatter: function() {
            return '<b>'+ this.series.name +'</b><br/>'+
            this.x +': '+ this.y +'Â°C';
          }
        },
        legend: {
          layout: 'vertical',
          align: 'right',
          verticalAlign: 'top',
          x: -10,
          y: 100,
          borderWidth: 0
        },
        series: [{
          name: 'Tokyo',
          data: [7.0, 6.9, 9.5, 14.5, 18.2, 21.5, 25.2, 26.5, 23.3, 18.3, 13.9, 9.6]
          }, {
            name: 'New York',
            data: [-0.2, 0.8, 5.7, 11.3, 17.0, 22.0, 24.8, 24.1, 20.1, 14.1, 8.6, 2.5]
            }, {
              name: 'Berlin',
              data: [-0.9, 0.6, 3.5, 8.4, 13.5, 17.0, 18.6, 17.9, 14.3, 9.0, 3.9, 1.0]
              }, {
                name: 'London',
                data: [3.9, 4.2, 5.7, 8.5, 11.9, 15.2, 17.0, 16.6, 14.2, 10.3, 6.6, 4.8]
                }]
              });

})
