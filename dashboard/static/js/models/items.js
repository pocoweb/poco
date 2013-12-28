App.Models.Item = Backbone.Model.extend({
  defaults: {
    api_key: '',
    item_id: '',
    item_name: '',
    market_price: '',
    image_link: ''
  },
  initialize: function() {
    this.set({api_key: $('#api_key').val()});
  },
  url: function() {
    return App.RestUrl + '/items/' + this.get('api_key') + '/id/' + this.get('item_id');
  }
});

App.Collections.Items = App.Collections.PaginatedCollection.extend({
//App.Models.Items = Backbone.Collection.extend({
  model: App.Models.Item,
  baseUrl: function() {
    this.api_key = $('#api_key').val();
    return App.RestUrl + '/items/' + this.api_key + '/';
  }
});

App.Models.ItemRec = Backbone.Model.extend({
  defaults: {
    rec_item_id: '',
    item_id: ''
  },
  initialize: function() {
    this.bind('destroy', this.drop);
  },
  drop: function() {
    is_on = this.get('is_black') ? false : true;
    $.getJSON(App.RestUrl + "/toggle_black_list2",
      {"api_key": $('#api_key').val(), "item_id1": this.get('rec_item_id'), "item_id2": this.get('item_id'), "is_on": is_on}
    );
  }
});

App.Models.ItemRecList = Backbone.Collection.extend({
  model: App.Models.ItemRec,
  rec_item_id: '',
  rec_type: '',
  initialize: function(models,options) {
    typeof(options) != 'undefined' || (options = {});
    typeof(options.rec_item_id) != 'undefined' ? this.rec_item_id = options.rec_item_id : this.rec_item_id = $('#item_id').val();
    typeof(options.rec_type) != 'undefined' ? this.rec_type = options.rec_type : this.rec_item_type = 'all';
    this.bind('reset', this.setRecItemId, this);
    this.bind('reset', this.setRecType, this);
    this.setRecItemId();
  },
  setRecItemId: function() {
    rec_item_id = this.rec_item_id;
    this.each(function(itemrec){
      itemrec.set({'rec_item_id': rec_item_id});
    });
  },
  setRecType: function() {
    rec_type = this.rec_type;
    this.each(function(itemrec){
      itemrec.set({'rec_type': rec_type});
    });
  },

  url: function() {
    return App.RestUrl + '/recs/' + $('#api_key').val() + '/id/' + this.rec_item_id + '/' + this.rec_type;
  },
  parse: function(resp) {
    return resp.rec_list[this.rec_type];
  }
});
