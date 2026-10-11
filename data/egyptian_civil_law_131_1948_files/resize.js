$(function() {
        resize_ten();
        resize_fifty();
        resize_thirtythree();
    });

// when window resizes
$(window).resize(function() {
        resize_ten();
        resize_fifty();
        resize_thirtythree();
    });
    
function resize_ten(){
        var tempHeight1=$(window).height()/3.5;
        $('.main_header_wrap').height(tempHeight1);
    };

function resize_fifty(){
        var tempHeight2=$(window).height()/1;
        $('.All_tables_wrap').height(tempHeight2);
    };

function resize_thirtythree(){
        var tempHeight3=$('.All_tables_wrap').height()/1.4;
        $('.table_heigh').height(tempHeight3);
    };