$(function(){
  $('#ooyalaplayer_2').closest('.image-explorer-hotspot').on('feedback:open', function (evt) {
      console.log("hello");
      OO.Player.create('ooyalaplayer_2', 'hiZ3lpeTplH2jtdlbzGNfTmmb0pW5zlW');
  }).on('feedback:close', function (evt) {
      OO.Player.create('ooyalaplayer_2').pause();
  });
  if (!window.OO) {
      require(['//player.ooyala.com/static/v4/production/core.js']);
  }
});
