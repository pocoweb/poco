App.Views.Item = Backbone.View.extend({
  model: {},
  initialize: function() {
    _.bindAll(this,'render');
    this.model.bind('change',this.render);
    $('#items_nav').text('商品详情');
  },
  render: function() {
    $('.popover').remove();
    $('.modal').remove();
    $('#main-content').html(_.template($('#item-template').html(),this.model.toJSON()));
    $('#my-modal').modal();
    rec_item_id = this.model.get('item_id');
    _.each(this.model.get('rec_lists'),function(collection, rec_type){
      var rec_list = new App.Models.ItemRecList(collection,{rec_item_id: rec_item_id, rec_type: rec_type});
      var rec_view = new App.Views.ItemRecList({collection: rec_list, rec_type: rec_type});

    });
   
    return this;
  }
});

App.Views.ItemRec = Backbone.View.extend({
  model: {},
  tagName: 'li',
  //template: _.template($('rec-item-template').html()),
  events: {
    "click span": "clear"
  },
  initialize: function() {
    this.model.bind('change', this.render, this);
    this.model.bind('destroy', this.remove, this);
  },
  clear: function(){
    this.model.destroy();
  },
  remove: function() {
    $(this.el).remove();
  },
  render: function() {
    $(this.el).html(_.template($('#rec-item-template').html(), this.model.toJSON()));
    try{
      $($(this.el).find("a[rel=popover]").attr('data-content')).load();
    }catch(e){};
    return this;
  }
});

App.Views.ItemRecList = Backbone.View.extend({
  collection: {},
  initialize: function() {
    this.collection.bind('remove', this.remove, this);
    this.collection.bind('reset', this.addAll, this);
    this.options.rec_type_id = this.options.rec_type.replace('_','-');
    this.render();
  },
  render: function() {
    $('.popover').remove();
    this.addAll();
  },
  addAll: function() {
    var rec_type_id = this.options.rec_type_id;
    $('#'+rec_type_id).html('');
    if(this.collection.length == 0) {
      $('#'+rec_type_id).html('<li style="padding:0">没有相关记录</li>');
    }
    else
    {
      this.collection.each(function(itemrec) {
        var view = new App.Views.ItemRec({model: itemrec});
        this.$('#'+rec_type_id).append(view.render().el);
      });
      $("a[rel=popover]").popover({
        offset: 21,
        placement: 'left',
        html: true,
        fallback: '',
        delayOut: 0,
        delayIn: 10
      });
    }
  },
  remove: function(itemrec) {
    if(this.options.rec_type_id != 'black-list')
    {
      var rec_list = new App.Models.ItemRecList([],{rec_item_id: itemrec.get('rec_item_id'), rec_type: 'black_list'});
      var rec_view = new App.Views.ItemRecList({collection: rec_list, rec_type: 'black_list'});
      rec_view.refresh();
      this.refresh();
    }
    else
    {
      //var rec_list = new App.Models.ItemRecList([],{rec_item_id: itemrec.get('rec_item_id'), rec_type: itemrec.get('rec_type')});
      //var rec_view = new App.Views.ItemRecList({collection: rec_list, rec_type: itemrec.get('rec_type')});
      //rec_view.refresh();
    }
  },
  refresh: function() {
    var rec_type_id = this.options.rec_type_id;
    var length = this.collection.length;
    //$('#'+rec_type_id).html('<div style="height:'+($('#'+rec_type_id).outerHeight()/length)*(length+1)+'px">&nbsp;<div>').fadeIn(3000);
    this.collection.fetch();
  }
});

App.Views.Items = Backbone.View.extend({
  collection: {},
  initialize: function() {
    _.bindAll(this,'render');
    this.collection.bind('reset',this.render);
    $('#items_nav').text('商品列表');
  },
  render: function() {
    $('#main-content').html('');
    var v = {items: this.collection.toJSON()};
    //$('#item-info').remove();
    //if($('#pagination').length > 0) {
    //  $('#pagination ul').remove();
    //  $('#items-info').remove();
    //}
    //else
    //{
      $('#main-content').append(_.template($('#pagination-template').html(), this.collection.pageInfo()));
    //}
    $('#item-search-text').focus();
    $('#item-search-text').val($('#search_name').val());
    $('#item-search').bind('submit',function(){App.Router.navigate('page/1?s='+$('#item-search-text').val(), true);return false;});
    $('#pagination').append(_.template($('#pagination-page-template').html(), this.collection.pageInfo()));
    $('#main-content').append(_.template($('#items-template').html(),v));
    $('#items-info table tr').each(function(){
      $($(this).find("a[rel=popover]").attr('data-content')).load();
    });
    $("a[rel=popover]").popover({
      offset: 10,
      placement: 'left',
      html: true,
      fallback: '',
      delayOut: 0,
      delayIn: 10
    });
    if($('#search_name').val() != ''){
      $("#pagination ul>li>a[rel=link]").each(function(){
        var href = $(this).attr('href');
        $(this).attr('href', href+'?s='+$('#search_name').val());
      });
    }
    return this;
  },
});

App.Views.UCG = Backbone.View.extend({
  model: {},
  initialize: function() {
    //_.bindAll(this,'render');
    //this.model.bind('change',this.render);
    $('#items_nav').text('编辑商品分类组别');
    this.render();
  },
  render: function() {
    $('.popover').remove();
    $('.modal').remove();
    $('#main-content').html(_.template($('#ucg-template').html()));
    $.getJSON(App.RestUrl + '/categroup', {"api_key": $('#api_key').val()}, function(data){
      $('#ucg-form textarea').val(data);
    });
    $('#ucg-form textarea').focus();
    $('#ucg-form').bind('reset',function(){
      $.getJSON(App.RestUrl + '/categroup', {"api_key": $('#api_key').val()}, function(data){
        $('#ucg-form textarea').val(data);
      });
      $('#ucg-form textarea').focus();
    });
    $('#ucg-form').bind('submit',function(){
      $.getJSON(App.RestUrl + '/update_category_groups2', 
        {"category_groups_src": $("#category_groups_src").val(),"api_key": $('#api_key').val()}, 
        function(data){
          $('#alert-message').removeClass('success important');
          if (data.is_succ) {
            $("#alert-message").addClass("success");
            $("#alert-message").html("已保存");
          }
          else {
            $("#alert-message").addClass("important");
            if (data.msg == "INVALID_FORMAT") {
                $("#alert-message").html("格式错误");
            }
            else if (data.msg == "INVALID_SITE"){
                $("#alert-message").html("该站点不存在");
            }
          }
          $('#alert-message').fadeIn('slow').fadeOut('slow');

          //$("#alert-message").toggle();
      });
      return false;
    });
    return this;
  }
});
