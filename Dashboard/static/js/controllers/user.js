App.Routers.User = Backbone.Router.extend({
  routes: {
      ":action_type": "defaultRoute",
  },
  defaultRoute: function( actions ){
    this.change_password();
  },
  change_password: function(){
    var view = new App.Views.UserChangePassword();
  }
});
