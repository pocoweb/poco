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
