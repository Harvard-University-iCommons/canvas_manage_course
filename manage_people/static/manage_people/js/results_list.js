/*
* JS for the Manage People - Add People form
* */
$(document).ready(function () {

    var usersFound = $('.user-select-checkbox', '#add_users_form').length;

    /*
    * Setup the form based on the number of users found. If there are no users, unhide the
    * users-not-found text. If one user was found, they will have a default role selection of
    * guest, so we enable the submit button. If multiple users were found, they will also have a
    * default role selection of guest, but the user will need to select which ones to add. The submit
    * button will be disabled until the user selects one or more users.
    * */
    if (usersFound) {
        $('.users-found').removeClass('hidden');
        if (usersFound == 1) {
            $('#user_create_button').removeClass('btn-disabled').addClass('btn-submit');
        }
        else if (usersFound > 1) {
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        }
    } else {
        $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        $('.users-not-found').removeClass('hidden');
    }

    /*
    * In the case where the user has multiple ids to add. Enable or disable the
    * submit button based how many checkboxes have been selected. If none are
    * selected, disable the button. If one or more are selected enable the button.
    * */
    $('.user-select-checkbox', '#add_users_form').click(function () {
        toggleAlert();
        if ($('.user-select-checkbox:checked').size() > 0 && $('#user_create_button').hasClass('btn-disabled')) {
            $('#user_create_button').removeClass('btn-disabled').addClass('btn-submit');
        }
        else if ($('#user_create_button').hasClass('btn-submit')) {
            $('#user_create_button').removeClass('btn-submit').addClass('btn-disabled');
        }
    });

    /*
    * When the user clicks submit we need to build the list of the users that are going to be added.
    * */
    $('#user_create_button').click(function (e) {
        toggleAlert();
        $('#user_create_button').button('loading');
        var usersToAdd = {};
        $('.user-select-checkbox:checked', '#add_users_form').each(function () {
            usersToAdd[$(this).val()] = $(this).closest('li').find('select').val();
        });
        // Update hidden input element with users to add
        $('#users_to_add').val(JSON.stringify(usersToAdd));
    });

    /*
    * Show the form containing any extra id's the user has that can be added to the course
    * */
    $('#form-show').click(function (e) {
        $('#cancel_add_to_course').addClass('hidden');
        $(this).addClass('hidden');
        $('form').removeClass('hidden');
    });

    /*
    * Hide the form containing any extra id's the user has that can be added to the course
    * */
    $('#form-hide').click(function (e) {
        $('form').addClass('hidden');
        $('#form-show').removeClass('hidden');
    });

    /*
    * Toggle alert messages in the case of errors
    * */
    function toggleAlert(errorName, state, errorElements) {
        if (typeof errorName == 'undefined') {
            $('.alert-lti').toggleClass('hidden', true);
            $('.alert-lti li').toggleClass('hidden', true);
            $("#matching-records li").toggleClass('has-error', false);
        } else {
            var $alert = $('.alert-lti').toggleClass('hidden', state);
            $alert.find('li.' + errorName).toggleClass('hidden', state);
            $(errorElements).each(function (index, $el) {
                $el.toggleClass('has-error', state);
            });
        }
    }
});
