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
