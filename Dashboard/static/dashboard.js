var chart;
var AppRouter = Backbone.Router.extend({
    routes: {
        "static/:site_id/:static_type": "getPost",
        "static/:site_id/:static_type/:days_ago": "getPost",
        "static/:site_id/:static_type/:from/:to": "getPost",
        "*actions": "defaultRoute" // Backbone will try match the route above first
    },
    getPost: function( id, type ) {
        // Note the variable in the route definition being passed in here
        alert( "Get post number " + id + type);   
    },
    defaultRoute: function( actions ){
        //alert( actions ); 
    }
});
// Instantiate the router
var app_router = new AppRouter;
// Start Backbone history a neccesary step for bookmarkable URL's
Backbone.history.start();

$(document).ready(function(){
	$('#widgetCalendar').DatePicker({
		date: new Date(),
  });
  
  var from_day = new Date();
  from_day.addDays(-30);

  var to_day = new Date();
  to_day.addDays(-1);
  
  var current_month = new Date();
  current_month.addMonths(-1);
  
  $('#widgetCalendar').DatePicker({
    flat: true,
		date: [new Date(from_day), new Date(to_day)],
    calendars: 3,
    current: new Date(current_month),
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
      console.log(formated);
			$('#widgetField span').get(0).innerHTML = formated.join(' -- ');
    },
    onRender: function(date) {
	  	return {
	  		disabled: (date.valueOf() > to_day.valueOf())
	  	}
	  }
  });
  var state = false;
  $('#confirm_range').bind('click', function(){
		$('#widgetCalendar').stop().animate({height: state ? 0 : $('#widgetCalendar div.datepicker').get(0).offsetHeight+30}, 200);
		state = !state;
		return false;
	});

  $('#widgetField>a').bind('click', function(){
		$('#widgetCalendar').stop().animate({height: state ? 0 : $('#widgetCalendar div.datepicker').get(0).offsetHeight+30}, 200);
		state = !state;
		return false;
  });

  chart = new Highcharts.Chart({
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
