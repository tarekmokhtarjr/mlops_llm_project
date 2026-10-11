

function printMe(event, id, recType, modelName, ProgVer, Lang) {

    event.preventDefault();

    // ======================================================
    // SVG Icons
    // ======================================================
    const IconGlobe = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#c8872a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`;
    const IconPhon  = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#c8872a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.4 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.54a16 16 0 0 0 6 6l.91-.91a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>`;

    // ======================================================
    // Print Footer — date/time computed client-side
    // ======================================================
    function buildPrintFooter() {
        const now  = new Date();
        const date = now.toLocaleDateString('en-GB');                          // dd/mm/yyyy  ← يطابق CONVERT(varchar,GETDATE(),103)
        const time = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }); // HH:MM ← يطابق CONVERT(varchar,GETDATE(),108)

        return `
            <div dir="rtl" style="
                border-top: 1px solid #ddd;
                margin-top: 30px;
                padding-top: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                color: #888;
                flex-wrap: wrap;
                gap: 8px;
            ">
                <div style="display:flex; align-items:center; gap:5px;">
                    ${IconGlobe}&nbsp;eastlaws.com
                </div>
                <div>${date}&nbsp;&nbsp;${time}</div>
                <div>All rights reserved | Eastlaws.com &copy; 2026 &nbsp;|&nbsp; &nbsp; ${IconPhon}: (+2) 01222224945</div>
            </div>`;
    }

    $.ajax({
        type: "GET",
        url: "/SideBtns/PrintMe",
        data: { recID: id, recType: recType, ModelName: modelName, Lang: Lang },
        beforeSend: function () { $("body").addClass("Printing"); },
        success: function (PrintHTML) {
            var myResult = PrintHTML[0].text;

            var iframe = document.createElement('iframe');
            iframe.style.position   = 'fixed';
            iframe.style.top        = '0';
            iframe.style.left       = '0';
            iframe.style.width      = '100%';
            iframe.style.height     = '100%';
            iframe.style.visibility = 'hidden';

            document.body.appendChild(iframe);

            iframe.onload = function () {
                var doc = iframe.contentDocument || iframe.contentWindow.document;

                var customHTML = `
                    <html dir="rtl" lang="ar">
                    <head>
                        <title>eastlaws.com</title>
                        <meta charset="utf-8">
                        <style>
                            .print_header .title_print p {
                                text-align: center;
                                font-weight: bold;
                                text-transform: uppercase;
                                font-size: 24px;
                                margin: 0;
                            }

                            .print-content h2 {
                                font-size: 22px;
                                margin: 30px 0 0;
                                line-height: 1.7;
                                background: #fff;
                                text-align: center;
                            }

                            .line_print  { margin: 10px 0; border: 1px dashed #ddd; }
                            .line_print2 { margin: 10px 0; border: 1px solid #ddd; }
                            .line_print3 { border: 1px double #ddd; }

                            .NO {
                                font-size: 20px;
                                font-weight: bold;
                                margin: 0;
                                line-height: 1;
                                background: #F8F8F8;
                                padding: 7px 15px;
                                display: inline-block;
                            }

                            .print-content p {
                                font-size: 18px;
                                margin: 0;
                                text-align: justify;
                                line-height: 1.5;
                            }

                            .main_title_print {
                                font-size: 22px;
                                line-height: 1.5;
                                margin-bottom: 0;
                                padding-bottom: 0;
                            }

                            .print_logo img {
                                width: 100px;
                                height: 100px;
                                display: block !important;
                                opacity: 1 !important;
                            }

                            .numbring {
                                font-size: 24px !important;
                                font-weight: bold;
                                color: #162542 !important;
                                border-bottom: 1px solid #ddd;
                            }

                            .title_print p  { text-align: center; }

                            .print_header img {
                                width: 250px;
                                display: block !important;
                                margin: 0 auto;
                                opacity: 1;
                            }

                            .print_copyright {
                                position: fixed;
                                top: 25%;
                                right: 15%;
                                width: 100%;
                                opacity: .7;
                            }

                            @page { margin: 1.5cm 1.5cm 1.5cm 2cm; }

                            .print_footer {
                                position: fixed;
                                bottom: 0;
                                left: 0;
                                right: 0;
                                text-align: center;
                                font-size: 14px;
                                padding: 10px 0 0;
                                background: #f8f8f8;
                                margin-top: 10px;
                                border-top: 1px solid #ddd;
                            }

                            .card_title {
                                font-size: 20px;
                                font-weight: bold;
                                color: #162542;
                                text-align: right;
                                border-bottom: 2px solid #d17632;
                                padding-bottom: 6px;
                                margin-bottom: 10px;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="print_page">
                            <div class="print_header" style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #c8872a; padding:10px 16px 8px 16px; margin-bottom:18px;">
                                <div style="font-size:20px; font-weight:bold; color:#c8872a; display:flex; align-items:center; gap:6px;">
                                    <img src="/Assets_${ProgVer}/main_layout/img/logo/printing_logo.png" style="width:150px;">
                                </div>
                                <div style="font-size:14px; color:#555;">E.L. Ref. No. : <span style="font-weight:bold; color:#111;">${id}</span></div>
                            </div>

                            <div class="print_content">
                                ${myResult}
                                ${buildPrintFooter()}
                            </div>
                        </div>
                        <div class="print_copyright">
                            <img src="/Assets_${ProgVer}/inner_layout/images/Watermark1.png">
                        </div>
                    </body>
                    </html>
                `;

                doc.open();
                doc.write(customHTML);
                doc.close();

                var img = doc.querySelector('.print_header img');
                var waitForImageLoad = function (callback) {
                    if (img && img.complete && img.naturalWidth > 0) {
                        callback();
                    } else if (img) {
                        img.onload = callback;
                    } else {
                        callback();
                    }
                };

                waitForImageLoad(function () {
                    $("body").removeClass("Printing");
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();

                    setTimeout(function () {
                        document.body.removeChild(iframe);
                    }, 500);
                });
            };

            iframe.src = 'about:blank';
            return false;
        },
        error: function () {
            $("body").removeClass("Printing");
        }
    });

    return false;
}



function copyMe(id, recType, modelName, Lang) {

    // Create a "hidden" input
    var mseg = 'تم النسخ بنجاح';
    if (Lang == 2) { mseg = 'The selected text was copied successfully'; }
    var aux = document.createElement("textarea");

    // aux.setAttribute("type", "textarea");
    $.ajax({
        type: "GET",
        url: "/SideBtns/CopyMe",
        data: { recID: id, recType: recType, ModelName: modelName, Lang: Lang },        
        success: function (result) {
            var str = result[0].text;
            var plainText = str.replace(/<[^>]*>/g, '\n');

            aux.innerHTML = plainText;
            document.body.appendChild(aux);
            aux.select();
            document.execCommand("copy");
            document.body.removeChild(aux);
            setTimeout(function () {
                alert(mseg);
            }, 0);
        }
    });
}






//  تجهيز الإضافة إلى الارشيف 
function prepareMeToArsheef(id, recType, modelName) {
    $("#ArcheefTableRecID_New").val('');
    getArsheefList();
    $("#SendMeArsheef_ID").val(id);
    $("#SendMeArsheef_RecType").val(recType);
    $("#SendMeArsheef_Model").val(modelName);
}




//  تجهيز الإضافة إلى التقرير  
function prepareMeToReport(id, recType, modelName) {
    $("#ReportTableRecID_New").val('');
    getReportList();
    $("#SendMeReport_ID").val(id);
    $("#SendMeReport_RecType").val(recType);
    $("#SendMeReport_Model").val(modelName);
}



//  تجهيز حفظ المستند للأغراض المحاسبية 

function prepareMeToAccounting(id, recType, modelName) {
    $("#AccountingTableRecID_New").val('');
    getAccountingList();
    $("#SendMeAccounting_ID").val(id);
    $("#SendMeAccounting_RecType").val(recType);
    $("#SendMeAccounting_Model").val(modelName);
}
