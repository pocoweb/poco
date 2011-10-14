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
