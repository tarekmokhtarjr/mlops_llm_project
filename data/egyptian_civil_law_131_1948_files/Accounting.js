


// الحصول على جدول التقرير
function getAccountingList() {
    var _myWhere = $("#AccountingListSearch").val();
    $.ajax({
        type: "GET",
        url: "/Accounting/GetAccountingList",
        data: { myWhere: _myWhere },
        success: function (result) {
            var html = "";
            for (var i = 0; i < result.length; i++) {
                html += "<tr id=myAccountingTable_" + result[i].id + " ondblclick=\"sendRecToAccounting()\"  onclick=\"selectAccountingRec(" + result[i].id + ")\" >"
                     +  "<td id=myAccountingTabletd_" + result[i].id + ">" + result[i].rowNum + "</td>"
                     +  "<td id=myAccountingTableName_" + result[i].id + " class=\"text-right\">" + result[i].name + "</td>"
                     +  "<td id=myAccountingTableRepNo_" + result[i].id + " class=\"text-right\">" + result[i].repNo + "</td>"
                    +  "<td id=myAccountingTableFileNo_" + result[i].id + " class=\"text-right\">" + result[i].fileNo + "</td>"
                     +  "<td>" + result[i].subCount + "</td></tr>";
            }
            $("#AccountingTablebody").html(html);

            var recID = $("#AccountingTableRecID_New").val();
            if (recID != '') selectAccountingRec(recID)
            else $("#myAccountingTable>tbody>tr:first").trigger('click');

            if ($("#AccountingTablebody").html() != '') {
                $("#btn_AccountingEdite").prop('disabled', false);
                $("#btn_AccountingDelete").prop('disabled', false);
            }
            else {
                $("#btn_AccountingEdite").prop('disabled', true);
                $("#btn_AccountingDelete").prop('disabled', true);
            }
        }
    });
}





// مسح البحث في قائمة التقرير 
function clearAccountingListSearch() {
    $("#AccountingListSearch").val("");
    getAccountingList();
}




//- تحديد سجل في التقرير 
function selectAccountingRec(e) {
    $('#myAccountingTable tbody tr').removeClass('tr_active');
    $("#myAccountingTable_" + e).addClass("tr_active");
    $("#AccountingTableRecID").val(e);
}



//----  تنفيذ عملية الإضافة أو التعديل في عنوان التقرير 
function Accounting_InsUpdate() {
    var myStatus = $('#Accounting_InsUpStatus').val();
    if (myStatus == 1) addNewTitInAccounting();
    if (myStatus == 2) updateTitAccounting();
}




// اضافة عنوان جديد في التقرير 
function prepare4AccountingNew() {
    $('#Accounting_InsUpStatus').val(1);
    $('#txtAddEditAccountingText').val('');
    $('#txtAddEditAccountingRepNo').val('');
    $('#txtAddEditAccountingFileNo').val('');
}



function addNewTitInAccounting() {
    var t = $('#txtAddEditAccountingText').val();
    var n = $('#txtAddEditAccountingRepNo').val();
    var f = $('#txtAddEditAccountingFileNo').val();
    $.ajax({
        type: "GET",
        url: "/Accounting/AddNewTit",
        data: { Name: t, RepNo: n, FileNo: f },
        success: function (result) {
            $('#AddEditAccountingText').modal("toggle");
            $("#AccountingTableRecID_New").val(result[0].id);
            getAccountingList();
        }
    });
}


//  تعديل العنوان المحدد  
function prepare4AccountingUpdate() {
    $('#Accounting_InsUpStatus').val(2);
    var id = $("#AccountingTableRecID").val();
    var t = $('#myAccountingTableName_' + id).html();
    var n = $('#myAccountingTableRepNo_' + id).html();
    var f = $('#myAccountingTableFileNo_' + id).html();
    $('#txtAddEditAccountingText').val(t);
    $('#txtAddEditAccountingRepNo').val(n);
    $('#txtAddEditAccountingFileNo').val(f);
}




function updateTitAccounting() {
    var t = $('#txtAddEditAccountingText').val();
    var n = $('#txtAddEditAccountingRepNo').val();
    var f = $('#txtAddEditAccountingFileNo').val();

    var id = $("#AccountingTableRecID").val();
    $.ajax({
        type: "GET",
        url: "/Accounting/UpdateTit",
        data: { recID: id, Name: t, RepNo: n, FileNo: f },
        success: function (result) {
            $('#AddEditAccountingText').modal("toggle");
            $("#AccountingTableRecID_New").val(result[0].id);
            getAccountingList();
            getIndexAccountingList();
        }
    });
}






//  حذف من قائمة التقرير 
function deleteFromAccountingList() {
    if (confirm('هل ترغب فعلا في حذف السجل الحالي ؟')) {
        var id = $("#AccountingTableRecID").val();
        $.ajax({
            type: "GET",
            url: "/Accounting/DeleteTit",
            data: { recID: id },
            success: function (result) {
                $("#AccountingTableRecID_New").val(result[0].id);
                getAccountingList();
                getIndexAccountingList();
            }
        });
    }
}





// إضافة السجل إلى التقرير
function addInfoRecToAccounting(lang) {
    // Define localized messages
    var messages = {
        R: lang == 2 ? "<p class=\"icon_Sad\"></p>The record already exists in this Accounting" : "السجل موجود في هذا التقرير من قبل",
        G: lang == 2 ? "Success<p class=\"icon_Happy\"></p>The record has been successfully added to the Accounting." : "تمت إضافة السجل إلى التقرير بنجاح"
    };

    // Collect form data
    var id = $("#AccountingTableRecID").val();
    var info_RecId = $("#SendMeAccounting_ID").val();
    var recType = $("#SendMeAccounting_RecType").val();
    var model = $("#SendMeAccounting_Model").val();

    // Send AJAX request
    $.ajax({
        type: "GET",
        url: "/SideBtns/AddRecToAccounting",
        data: { masterID: id, recID: info_RecId, recType: recType, ModelName: model },
        success: function (result) {
            if (result[0].text == '-1') {
                ShowMyMessage(messages.R, "R");
            } else {
                ShowMyMessage(messages.G, "G");
            }
            $("#AccountingTableRecID_New").val(id);
            getAccountingList();
        },
        error: function (xhr, status, error) {
            // Log and display a meaningful error message
            console.error("Error occurred: ", error);
            ShowMyMessage(lang == 2 ? "<p class=\"icon_Sad\"></p>An error occurred while processing the request." : "حدث خطأ أثناء معالجة الطلب.", "R");
        }
    });
}

