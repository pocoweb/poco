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
      case 'rec': return this.rec_dict();
      case 'avg_order_total': return this.avg_order_total_dict();
      case 'total_sales': return this.total_sales_dict();
      case 'unique_sku': return this.unique_sku_dict();

      case 'recvav':  return this.rec_by_type_dict(this.options.dict_type,'看了也看');
      case 'recph':   return this.rec_by_type_dict(this.options.dict_type,'根据购买历史');
      case 'recbab':  return this.rec_by_type_dict(this.options.dict_type,'买了也买');
      case 'recbtg':  return this.rec_by_type_dict(this.options.dict_type,'一起买');
      case 'recvub':  return this.rec_by_type_dict(this.options.dict_type,'看了最终买');     
      case 'recbobh': return this.rec_by_type_dict(this.options.dict_type,'根据浏览历史');
      case 'recsc':   return this.rec_by_type_dict(this.options.dict_type,'根据购物车');
      case 'rec_sales': return this.rec_sales_dict();
      default: return {};
    }
  },
  pv_uv_dict: function() {
    return {
      chart: {
        renderTo: "chart-container"
      },
      title: {
        text: "商品PV和UV图",
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
  rec_dict: function(){
    var sum_pv_v_wo = 0;
    var sum_clickrec = 0;
    for (var index in this.options.data.series.pv_v) {
        if (this.options.data.series.pv_v[index] != null) {
            if (this.options.data.series.clickrec[index] != null) {
                sum_pv_v_wo += this.options.data.series.pv_v[index] - this.options.data.series.clickrec[index];
                sum_clickrec += this.options.data.series.clickrec[index];
            }
        }
    }
    var per_pv_v_wo = Math.round(sum_pv_v_wo / (sum_pv_v_wo + sum_clickrec) * 1000) / 10;
    var per_clickrec = Math.round(sum_clickrec / (sum_pv_v_wo + sum_clickrec) * 1000) / 10;

    return chart_dict = {
      chart: {
        renderTo: "chart-container",
      },
      title: {
        text: "商品推荐占PV数",
      },
      subtitle: {
        //text: site_id,
        x: -20
      },
      xAxis: {
        categories: this.options.data.categories,
      },
      yAxis: [{
        title: {
          text: '次数'
        },
        plotLines: [{
          value: 0, width: 1, color: '#808080'
        }]
        },
        {
          title: {
            text: '比率'
          },
          plotLines: [{
            value: 0, width: 1, color: '#808080'
            }],
            opposite: true
          }
          ],
          tooltip: {
            formatter: function() {
              if (this.point.name) {
                var percentage = 0;
                if (this.point.name == "非推荐PV") {
                  percentage = "" + per_pv_v_wo + "%";
                }
                else {
                  percentage = "" + per_clickrec + "%";
                };

                return this.point.name + ":" + this.y + '次, 占' + percentage;

              }
              else {
                return '<b>' + this.series.name + '</b><br/>' +
                this.x + ':' + this.y + '';
              }
            }
          },
          series: [{
            "name": "商品PV数",
            "data": this.options.data.series.pv_v,
            "type": "area"
          },
          {
            "name": "推荐点击数",
            "data": this.options.data.series.clickrec,
            "type": "area"
          },
          {
            "name": "推荐点击占PV比",
            "data": this.options.data.series.clickrec_pv_ratio,
            "type": "spline",
            "yAxis": 1
          },
          {
            "type": "pie",
            "name": "汇总",
            "data": [
              {
                name: "非推荐PV",
                y: sum_pv_v_wo,
                color: '#058dc7'
                //color: highchartsOptions.colors[0]
            },
            {
              name: "推荐点击PV",
              y: sum_clickrec,
              color: '#50b432'
              //color: highchartsOptions.colors[1]
          }],
          center: [30, 30],
          size: 60,
          showInLegend: true,
          dataLabels: {
          enabled: false
          }
        }
      ]
    };
  },

  avg_order_total_dict: function() {
    return {
      chart: {
          renderTo: "chart-container",
      },
      title: {
          text: "平均客单价",
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
          "data": this.options.data.series.avg_order_total,
          "type": "spline",
          "dataLabels": {
            enabled: false
           }
         },
         {
           "name": "有无推荐客单价差",
           "data": this.options.data.series.avg_order_total_rec_delta,
           "type": "spline",
           "dataLabels": {
             enabled: false
           },
           "yAxis": 1
         }
       ]
    }
  },
  total_sales_dict: function() {
    var sum_total_sales_without_rec = 0;
    var sum_total_sales_rec_delta = 0;
    for (var index in this.options.data.series.total_sales) {
        if (this.options.data.series.total_sales[index] != null) {
            if (this.options.data.series.total_sales_rec_delta[index] != null) {
                sum_total_sales_without_rec += this.options.data.series.total_sales[index] - this.options.data.series.total_sales_rec_delta[index];
                sum_total_sales_rec_delta += this.options.data.series.total_sales_rec_delta[index];
            }
        }
    }
    
    sum_total_sales_without_rec = Math.round(sum_total_sales_without_rec * 100) / 100;
    sum_total_sales_rec_delta = Math.round(sum_total_sales_rec_delta * 100) / 100;

    var per_total_sales_without_rec = Math.round(sum_total_sales_without_rec / (sum_total_sales_without_rec + sum_total_sales_rec_delta) * 1000) / 10;
    var per_total_sales_rec_delta = Math.round(sum_total_sales_rec_delta / (sum_total_sales_without_rec + sum_total_sales_rec_delta) * 1000) / 10;
    return {
      chart: {
        renderTo: "chart-container",
      },
      title: {
        text: "总销售金额",
      },
      subtitle: {
        //text: site_id,
        x: -20
      },
      xAxis: {
        categories: this.options.data.categories,
      },
      yAxis: [{
          title: {
          text: '金额'
          },
          plotLines: [{
          value: 0, width: 1, color: '#808080'
          }]
        },{
          title: {
          text: '比率'
          },
          plotLines: [{
          value: 0, width: 1, color: '#808080'
          }],
          opposite: true
        }],
       tooltip: {
         formatter: function() {
           if (this.point.name) {
             var percentage = 0;
             if (this.point.name == "非推荐销售金额") {
               percentage = "" + per_total_sales_without_rec + "%";
             }
             else {
               percentage = "" + per_total_sales_rec_delta + "%";
             };
             return this.point.name + ":" + this.y + '元, 占' + percentage;
           }
           else {
             return '<b>' + this.series.name + '</b><br/>' +
             this.x + ':' + this.y + '';
           }
          }
        },
        series: [{
          "name": "总销售金额",
          "data": this.options.data.series.total_sales,
          "type": "area",
          "dataLabels": {enabled: false}
        },{
          "name": "有无推荐销售金额差",
          "data": this.options.data.series.total_sales_rec_delta,
          "type": "area",
          "dataLabels": {enabled: false}
        },{
          "name": "推荐贡献比率",
          "data": this.options.data.series.total_sales_rec_delta_ratio,
          "type": "spline",
          "dataLabels": {enabled: false },
          yAxis: 1
        },{
          "type": "pie",
          "name": "汇总",
          "data": [{
            name: "非推荐销售金额",
            y: sum_total_sales_without_rec,
            color: '#058dc7'
          },{
            name: "推荐销售金额",
            y: sum_total_sales_rec_delta,
            color: '#50b432'}],
          center: [30, 30],
          size: 60,
          showInLegend: true,
          "dataLabels": {enabled: false }
        }
      ]
    };
  },
  unique_sku_dict: function(){
    return {
      chart: {
        renderTo: "chart-container",
      },
      title: {
        text: "平均Unique SKU",
      },
      subtitle: {
        //text: site_id,
        x: -20
      },
      xAxis: {
        categories: this.options.data.categories,
      },
      yAxis: [{
        title: {
          text: '平均Unique SKU'
        },
        plotLines: [{
          value: 0, width: 1, color: '#808080'
        }]
      }
      ],
      tooltip: {
        formatter: function() {
          return '<b>' + this.series.name + '</b><br/>' +
          this.x + ':' + this.y;
        }
      },
      series: [{
        "name": "平均Unique SKU",
        "data": this.options.data.series.avg_unique_sku,
        "type": "spline"
      },
      {
        "name": "平均商品件数",
        "data": this.options.data.series.avg_item_amount,
        "type": "spline"
      }
    ]};
  },
  rec_by_type_dict: function(action_name,title){
    return {
      chart: {
        renderTo: "chart-container",
      },
      title: {
        text: title,
      },
      subtitle: {
        //text: site_id,
        x: -20
      },
      xAxis: {
        categories: this.options.data.categories,
      },
      yAxis: [{
          title: {
          text: '次数'
        },
          plotLines: [{
          value: 0, width: 1, color: '#808080'
        }]},
        {
          title: {
            text: '点击/请求比'
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
          this.x + ':' + this.y;
        }
      },
      series: [{
        "name": "推荐请求数",
        "data": this.options.data.series["recommendation_request_count_"+action_name],
        "type": "area"
      },
      {
        "name": "推荐展示数",
        "data": this.options.data.series["recommendation_show_count_"+action_name],
        "type": "area"
      },
      {
        "name": "推荐点击数",
        "data": this.options.data.series["click_rec_count_"+action_name],
        "type": "area"
      },
      {
        "name": "推荐点击/请求比",
        "data": this.options.data.series["click_rec_show_ratio_"+action_name],
        "type": "spline",
        yAxis: 1
      }
    ]};
  },
  rec_sales_dict: function() {
    return {
      chart: {
        renderTo: "chart-container"
      },
      title: {
        text: "推荐金额",
      },
      xAxis: {
        categories: this.options.data.categories,
      },
      yAxis: {
        title: {
          text: '金额'
        }
      },
      tooltip: {
        formatter: function() {
          return '<b>' + this.series.name + '</b><br/>' +
          this.x + ':' + this.y + '元';
        }
      },
      series: [{
        "name": "推荐金额",
        "data": this.options.data.series.total_sales_rec_delta,
        "type": "area"
      }]
    };
  },

});

