App.Routers.Items = Backbone.Router.extend({
  routes: {
      "page": "page",
      "page/:page_num?s=:search_name": "page",
      "page/:page_num": "page",
      "id/:item_id": "view_item",
      "ucg": "ucg",
      ":action_type": "defaultRoute",
  },
  defaultRoute: function( actions ){
    this.page();
  },
  page: function(page_num, search_name) {
    if(typeof(page_num) == 'undefined' || page_num <= 0) var page_num = 1;
    if(typeof(search_name) == 'undefined') var search_name = '';
    $('#search_name').val(search_name);
    var items = new App.Collections.Items();
    var items_view = new App.Views.Items({collection: items});
    items.fetch({data: {page_num: page_num, page_size: 15, search_name: search_name}});
  },
  view_item: function(item_id) {
    var item = new App.Models.Item({item_id: item_id});
    var item_view = new App.Views.Item({model: item});
    item.fetch();
  },
  // update category group
  ucg: function(){
    var cg = {};
    var ucg_view = new App.Views.UCG({model: cg});
  }
  /*
  getPost: function(report_type, report_date) {
    var r = new App.Models.Report;
    if(typeof(report_type) !== 'undefined' && report_type !== '') r.set({'report_type': report_type});
    if(typeof(report_date) !== 'undefined' && report_date !== '') r.set({'report_date': report_date});
    $('#report_type').val(r.get('report_type'));
    var report_view = new App.Views.Report({model: r});
    r.fetch({
      success: function(model,response){
        r.set({data:response});
      },
      error: function(){
        alert('服务器忙，请稍后再试');
      }
    });
  },
  */
});
