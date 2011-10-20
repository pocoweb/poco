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

Highcharts.theme = {
  chart: {
    margin: [60, 80, 60, 65]
    },
    //colors: ['#005BC8', '#54B428', '#B7461C', '#FF9655', '#54B428', '#64E572', '#FF9655', '#FFF263', '#6AF9C4'],
    //colors: ['#058DC7', '#50b432', '#ed7e17', '#FF9655', '#50b432', '#64E572', '#FF9655', '#FFF263', '#6AF9C4'],
    //colors: ["#7798BF", "#55BF3B", "#DF5353", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#7798BF", "#aaeeee"],

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
    y: 20,
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
  title: {
    margin: 50,
    style: { 
      //color: '#000',
      font: 'bold 16px "Trebuchet MS", Verdana, sans-serif'
    }
  },
  subtitle: {
    x: -20,
    style: { 
      font: 'bold 12px "Trebuchet MS", Verdana, sans-serif'
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

var App = {
  Models: {},
  Views: {},
  Routers: {},
  Collections: {},
  RestUrl: '/ajax',
  Router: {},
  initialize: function(Router) {
    this.Router = new Router;
    Backbone.history.start();
  }
};

// includes bindings for fetching/fetched

App.Collections.PaginatedCollection = Backbone.Collection.extend({
  initialize: function() {
    _.bindAll(this, 'parse', 'url', 'pageInfo', 'nextPage', 'previousPage');
    typeof(options) != 'undefined' || (options = {});
    typeof(this.page_size) != 'undefined' || (this.page_size = 10);
    typeof(this.page_num) != 'undefined' || (this.page_num = 1);
  },
  fetch: function(options) {
    typeof(options) != 'undefined' || (options = {});
    this.trigger("fetching");
    var self = this;
    var success = options.success;
    options.success = function(resp) {
      self.trigger("fetched");
      if(success) { success(self, resp); }
    };
    return Backbone.Collection.prototype.fetch.call(this, options);
  },
  parse: function(resp) {
    this.page_num = resp.page;
    this.page_size = resp.page_size;
    this.total = resp.total;
    return resp.models;
  },
  url: function() {
     return this.baseUrl();
  },
  pageInfo: function() {
    var info = {
      total: this.total,
      page_num: this.page_num,
      page_size: this.page_size,
      pages: Math.ceil(this.total / this.page_size),
      prev: false,
      next: false
    };

    var max = Math.min(this.total, this.page_num * this.page_size);

    if (this.total == this.pages * this.page_size) {
      max = this.total;
    }

    info.range = [(this.page_num - 1) * this.page_size + 1, max];

    if (this.page_num > 1) {
      info.prev = this.page_num - 1;
    }

    if (this.page_num < info.pages) {
      info.next = this.page_num + 1;
    }

    return info;
  },
  nextPage: function() {
    if (!this.pageInfo().next) {
      return false;
    }
    this.page_num = this.page_num + 1;
    return this.fetch();
  },
  previousPage: function() {
    if (!this.pageInfo().prev) {
      return false;
    }
    this.page_num = this.page_num - 1;
    return this.fetch();
  }
});
