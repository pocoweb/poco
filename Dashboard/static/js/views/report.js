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
