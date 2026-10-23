


//--------  الحصول على عنوان التشريع بدلالة الرقم الكودي له 
function getTashTit(recType, id) {
    $.ajax({
        type: "GET",
        url: "/Tash/GetTashTit",
        data: { RecID: id, RecType: recType },
        success: function (result) {
            $("#TashTit").html(result);
        }
    });
}




//------  البحث برقم المادة 
function goToMadaNo(recType, id) {
    var MadaNo = $("#searchBySubNo").val();
    $.ajax({
        type: "GET",
        url: "/Tash/GetTashMadaID",
        data: { RecID: id, RecType: recType, MadaNo: MadaNo },
        success: function (result) {
            var MadaID = result;

            goToMadaID(MadaID);

            $('.side_Switch').css({ 'left': '-300px' });
        }
    });
}




//------  البحث بكود المادة
function goToMadaID(MadaID) {
    var target = $("#MadaNoRep_" + MadaID);
    if (target.length === 0) { return;} // Check if the element exists

    $('html, body').animate({scrollTop: target.offset().top}, 100); // Adjust 500 to control scroll speed
}





function getTashFullText(recType, id, MadaID) {

    var _colorText = $("#colorText").html()

    $.ajax({
        type: "GET",
        url: "/Tash/GetFullText",
        data: { RecID: id, RecType: recType, colorText: _colorText },
        beforeSend: function () {
            $("body").addClass("loading");
        },
        success: function (ui) {
            $("#FullText").html(ui);
            $("body").removeClass("loading");
            goToMadaID(MadaID);
            getFehres(false);
        },
        error: function (error) {
            $("body").removeClass("loading");
        }
    });
    
}



//-------  البحث بنصوص المواد 
function getFullTextBySearch() {
    var id        = $("#recID").val();
    var recType   = $("#recType").val();
    var whereText = $("#txt_FullTextSearch").val();
    var whereOption = $("input[name='Search_radio_btns']:checked").val();
    var colorText = $("#colorText").html();
    $.ajax({
        type: "GET",
        url: "/Tash/GetFullTextBySearch",
        data: { RecID: id, RecType: recType, WhereText: whereText, ColorText: colorText, WhereOption: whereOption },
        beforeSend: function () {
            $("body").addClass("loading");
        },
        success: function (ui) {
            $("#MawaadTextOnly").html(ui);
            if (whereText == "") { $("#lbl_CearSearchHint").addClass("hidden"); } else $("#lbl_CearSearchHint").removeClass("hidden");  
            
            $("body").removeClass("loading");
            },
        error: function (error) {
            $("body").removeClass("loading");
            ShowMyMessage("تعذر العثور على نتائج لعملية البحث ... برجاء التأكد من عناصر البحث ثم تكرار المحاولة", "R"); 
        }
    });
}


//--------  مسح البحث في نصوص المواد   
function clearSearchFullText() {

    $("#txt_FullTextSearch").val("");   
    getFullTextBySearch();

}


//------ مسح 
function clearSearchMadaNo() {
    $("#txtMadaNo").val("");
}


//------  اذهب إلى مادة رقم  
function goToMadaByNo() {
    var MadaNo  = $("#txtMadaNo").val();
    var id      = $("#recID").val();
    var recType = $("#recType").val();

    $.ajax({
        type: "GET",
        url: "/Tash/GetTashMadaID",
        data: { RecID: id, RecType: recType, MadaNo: MadaNo },
        success: function (result) {
            var MadaID = result;

            goToMadaID(MadaID);

            $('.side_Switch').css({ 'left': '-300px' });
        }
    });
}
