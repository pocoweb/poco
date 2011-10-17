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
    var chart_dict = (new App.Views.Chart({dict_type: this.model.get('report_type'), data: data})).render_dict();
    var chart_temp = new App.Models.DayChart({chart_dict: chart_dict});
    return this;
  },

  renderChartTable: function(){
    var data = this.model.get('data');
  }
});

App.Views.Chart = Backbone.View.extend({
  dict_type: '',
  data: {},
  render_dict: function()
  {
    switch(this.options.dict_type)
    {
      case 'pv_uv': return this.pv_uv_dict();
      case 'plo': return this.plo_dict();
      case 'avg_order_total': return this.avg_order_total_dict();
      default: return {};
    }
  },

  pv_uv_dict: function() {
    return {
      chart: {
        renderTo: "chart-container"
      },
      title: {
        text: "商品PV和UV图"
      },
      xAxis: {
        categories: this.options.data.categories,
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
        "data": this.options.data.series.pv_v,
        "type": "area"
      },{
        "name": "商品UV",
        "data": this.options.data.series.uv_v,
        "type": "area",
      },{
        "name": "PV/UV",
        "data": this.options.data.series.pv_uv,
        "type": "line",
        yAxis: 1
      }]
    };
  },
  plo_dict: function() {
    return {
      chart: {
        renderTo: "chart-container"
      },
      title: {
        text: "商品订单数",
      },
      xAxis: {
        categories: this.options.data.categories,
      },
      yAxis: [{
        title: {
          text: '订单数'
        }
      },
      {
        title: {
          text: '比率'
        },
        opposite: true
      }
      ],
      tooltip: {
        formatter: function() {
          return '<b>' + this.series.name + '</b><br/>' +
          this.x + ':' + this.y + '单';
        }
      },
      series: [{
        "name": "订单数",
        "data": this.options.data.series.pv_plo,
        "type": "column"
      },
      {"name": "订单数/商品UV",
        "data": this.options.data.series.pv_plo_d_uv,
        "type": "spline",
        yAxis: 1
      }]
    }
  },
  avg_order_total_dict: function() {
    return {
      chart: {
          renderTo: "chart-container",
      },
      title: {
          text: "平均客单价",
          x: -20
      },
      subtitle: {
          x: -20
      },
      xAxis: {
          categories: this.options.data.categories,
      },
      yAxis: [
        {
          title: {
            text: '客单价'
          },
          plotLines: [{
            value: 0, width: 1, color: '#808080'
          }]
        },
        {
          title: {
            text: '客单价差'
          },
          plotLines: [{
            value: 0, width: 1, color: '#808080'
          }],
          opposite: true
        }
      ],
      tooltip: {
        formatter: function() {
          return '<b>' + this.series.name + '</b><br/>' +
          this.x + ':' + this.y + '元';
        }
      },
      series: [
        {
          "name": "客单价",
          "data": this.options.data.avg_order_total,
          "type": "spline",
          "dataLabels": {
            enabled: false
           }
         },
         {
           "name": "有无推荐客单价差",
           "data": this.options.data.avg_order_total_rec_delta,
           "type": "spline",
           "dataLabels": {
             enabled: false
           },
           "yAxis": 1
         }
       ]
    }
  }
});



