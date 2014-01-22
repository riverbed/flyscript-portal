/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */


// ref http://stackoverflow.com/a/10124151/2157429
function confirm(heading, question, cancelButtonTxt, okButtonTxt, callback) {

    var confirmModal =
      $('<div class="modal hide fade">' +
          '<div class="modal-header">' +
            '<a class="close" data-dismiss="modal">&times;</a>' +
            '<h3>' + heading +'</h3>' +
          '</div>' +

          '<div class="modal-body">' +
            '<p>' + question + '</p>' +
          '</div>' +

          '<div class="modal-footer">' +
            '<a href="#" class="btn" data-dismiss="modal">' +
              cancelButtonTxt +
            '</a>' +
            '<a href="#" id="okButton" class="btn btn-primary">' +
              okButtonTxt +
            '</a>' +
          '</div>' +
        '</div>');

    confirmModal.find('#okButton').click(function(event) {
      callback();
      confirmModal.modal('hide');
    });

    confirmModal.modal('show');
};

function loadingModal(heading, text) {

    var confirmModal =
      $('<div class="modal hide fade">' +
          '<div class="modal-header">' +
            '<h3>' + heading +'</h3>' +
          '</div>' +

          '<div class="modal-body">' +
            '<p class="text-center">' + text + '</p>' +
            '<p class="text-center">'  +
               '<img src="/static/showLoading/images/loading.gif">' +
            '</p>' +
          '</div>' +

          '<div class="modal-footer">' +
            '&nbsp;' +
          '</div>' +
        '</div>');

    return confirmModal;
};

function reloadingModal(url, allReports) {
    if (allReports) {
        modal = loadingModal('Reloading All Reports', 'Please wait ...');
    } else {
        modal = loadingModal('Reloading Report', 'Please wait ...');
    }

    modal.modal('show');
    var next = window.location.href;
    window.location.href = url + "?next=" + next;
};
