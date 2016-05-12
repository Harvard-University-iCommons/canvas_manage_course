$(document).ready(function() {
    $('button').bind('click', function (e) {
        $('#lti-custom-error').addClass('hide');

        //email or 8 digits regex
        var emailHuid = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))|\d{8}$/;

        var $eleInput = $('#emailHUID');

        if ($('#msg-not-found').is(":visible")) {
            $('#msg-not-found').addClass('hidden');
        }

        if (!(emailHuid.test($eleInput.val().trim()))) {
            $("label[for='" + $eleInput.attr('id') + "']").addClass('text-strong-error');
            $eleInput.parent().addClass('has-error');
            $('#alert-invalid-input').removeClass('hidden');
            e.preventDefault();
        } else {
            $('.alert-lti').addClass('hidden');
            $("label[for='" + $eleInput.attr('id') + "']").removeClass('text-strong-error');
            $eleInput.parent().removeClass('has-error');
            $('#user_search_button').button('loading');
        }

    });

    $('#user_search_button').button('reset');
});
