




var fixmeTop = $('.fixme').offset().top;
$(window).scroll(function () {
    var currentScroll = $(window).scrollTop();
    if (currentScroll >= fixmeTop) {
        $('.fixme').css({
            position: 'fixed',
            top: '0',
            left: '35px',
            width: '23%',
            background: '#fff',
            transition: 'none'

        });
    } else {
        $('.fixme').css({
            position: 'static',
            width: '100%'
        });
    }
});