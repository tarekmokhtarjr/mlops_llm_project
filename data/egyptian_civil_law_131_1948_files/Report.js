


// الحصول على جدول التقرير
function getReportList() {
    var _myWhere = $("#ReportListSearch").val();
    $.ajax({
        type: "GET",
        url: "/Report/GetReportList",
        data: { myWhere: _myWhere },
        success: function (result) {
            var html = "";
            for (var i = 0; i < result.length; i++) {
                html += "<tr id=myReportTable_" + result[i].id + " ondblclick=\"sendRecToReport()\"  onclick=\"selectReportRec(" + result[i].id + ")\" >"
                     +  "<td id=myReportTabletd_" + result[i].id + ">" + result[i].rowNum + "</td>"
                     +  "<td id=myReportTableName_" + result[i].id + " class=\"text-right\">" + result[i].name + "</td>"
                     +  "<td id=myReportTableRepNo_" + result[i].id + " class=\"text-right\">" + result[i].repNo + "</td>"
                     +  "<td id=myReportTableFileNo_" + result[i].id + " class=\"text-right\">" + result[i].fileNo + "</td>"
                     +  "<td>" + result[i].subCount + "</td></tr>";
            }
            $("#ReportTablebody").html(html);

            var recID = $("#ReportTableRecID_New").val();
            if (recID != '') selectReportRec(recID)
            else $("#myReportTable>tbody>tr:first").trigger('click');

            if ($("#ReportTablebody").html() != '') {
                $("#btn_ReportEdite").prop('disabled', false);
                $("#btn_ReportDelete").prop('disabled', false);
            }
            else {
                $("#btn_ReportEdite").prop('disabled', true);
                $("#btn_ReportDelete").prop('disabled', true);
            }
        }
    });
}





// مسح البحث في قائمة التقرير 
function clearReportListSearch() {
    $("#ReportListSearch").val("");
    getReportList();
}




//- تحديد سجل في التقرير 
function selectReportRec(e) {
    $('#myReportTable tbody tr').removeClass('tr_active');
    $("#myReportTable_" + e).addClass("tr_active");
    $("#ReportTableRecID").val(e);
}



//----  تنفيذ عملية الإضافة أو التعديل في عنوان التقرير 
function report_InsUpdate() {
    var myStatus = $('#Report_InsUpStatus').val();
    if (myStatus == 1) addNewTitInReport();
    if (myStatus == 2) updateTitReport();
}




// اضافة عنوان جديد في التقرير 
function prepare4ReportNew() {
    $('#Report_InsUpStatus').val(1);
    $('#txtAddEditReportText').val('');
    $('#txtAddEditReportRepNo').val('');
    $('#txtAddEditReportFileNo').val('');
}



function addNewTitInReport() {
    var t = $('#txtAddEditReportText').val();
    var n = $('#txtAddEditReportRepNo').val();
    var f = $('#txtAddEditReportFileNo').val();
    $.ajax({
        type: "GET",
        url: "/Report/AddNewTit",
        data: { Name: t, RepNo: n, FileNo: f },
        success: function (result) {
            $('#AddEditReportText').modal("toggle");
            $("#ReportTableRecID_New").val(result[0].id);
            getReportList();
        }
    });
}


//  تعديل العنوان المحدد  
function prepare4ReportUpdate() {
    $('#Report_InsUpStatus').val(2);
    var id = $("#ReportTableRecID").val();
    var t = $('#myReportTableName_' + id).html();
    var n = $('#myReportTableRepNo_' + id).html();
    var f = $('#myReportTableFileNo_' + id).html();
    $('#txtAddEditReportText').val(t);
    $('#txtAddEditReportRepNo').val(n);
    $('#txtAddEditReportFileNo').val(f);
}




function updateTitReport() {
    var t = $('#txtAddEditReportText').val();
    var n = $('#txtAddEditReportRepNo').val();
    var f = $('#txtAddEditReportFileNo').val();

    var id = $("#ReportTableRecID").val();
    $.ajax({
        type: "GET",
        url: "/Report/UpdateTit",
        data: { recID: id, Name: t, RepNo: n, FileNo: f },
        success: function (result) {
            $('#AddEditReportText').modal("toggle");
            $("#ReportTableRecID_New").val(result[0].id);
            getReportList();
            getIndexReportList();
        }
    });
}






//  حذف من قائمة التقرير 
function deleteFromReportList() {
    if (confirm('هل ترغب فعلا في حذف السجل الحالي ؟')) {
        var id = $("#ReportTableRecID").val();
        $.ajax({
            type: "GET",
            url: "/Report/DeleteTit",
            data: { recID: id },
            success: function (result) {
                $("#ReportTableRecID_New").val(result[0].id);
                getReportList();
                getIndexReportList();
            }
        });
    }
}





// إضافة السجل إلى التقرير
function addInfoRecToReport(lang) {
    // Define localized messages
    var messages = {
        R: lang == 2 ? "<p class=\"icon_Sad\"></p>The record already exists in this report" : "السجل موجود في هذا التقرير من قبل",
        G: lang == 2 ? "Success<p class=\"icon_Happy\"></p>The record has been successfully added to the report." : "تمت إضافة السجل إلى التقرير بنجاح"
    };

    // Collect form data
    var id = $("#ReportTableRecID").val();
    var info_RecId = $("#SendMeReport_ID").val();
    var recType = $("#SendMeReport_RecType").val();
    var model = $("#SendMeReport_Model").val();

    // Send AJAX request
    $.ajax({
        type: "GET",
        url: "/SideBtns/AddRecToReport",
        data: { masterID: id, recID: info_RecId, recType: recType, ModelName: model },
        success: function (result) {
            if (result[0].text == '-1') {
                ShowMyMessage(messages.R, "R");
            } else {
                ShowMyMessage(messages.G, "G");
            }
            $("#ReportTableRecID_New").val(id);
            getReportList();
        },
        error: function (xhr, status, error) {
            // Log and display a meaningful error message
            console.error("Error occurred: ", error);
            ShowMyMessage(lang == 2 ? "<p class=\"icon_Sad\"></p>An error occurred while processing the request." : "حدث خطأ أثناء معالجة الطلب.", "R");
        }
    });
}

