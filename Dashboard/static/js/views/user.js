App.Views.UserChangePassword = Backbone.View.extend({
  model: {},
  initialize: function() {
    $('#items_nav').text('修改密码');
    this.render();
  },
  render: function() {
    $('#main-content').html(_.template($('#change-password-template').html()));
    $('#change-password-form').bind('submit',function(){
      $.post(
        App.RestUrl + '/change_password',
        {'password': $('#password').val(),'password_confirm': $('#password_confirm').val()},
        function(data){
          $('#alert-message').removeClass('success important');
          if (data.is_succ) {
            $("#alert-message").addClass("success");
          }
          else {
            $("#alert-message").addClass("important");
          }
          $("#alert-message").html(data.msg);
          $('#alert-message').fadeIn('slow').fadeOut('slow');
          },
        "json");
       return false;
     });
   return this;
  }
});
