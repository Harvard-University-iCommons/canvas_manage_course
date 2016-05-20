$(document).ready(function() {
    var userlistURL = window.globals.userlistURL;
    var classlistURL  = window.globals.classlistURL;
    var addToSectionURL = window.globals.addToSectionURL;
    var rmFromSectionURL = window.globals.rmFromSectionURL;

    function showIfNone() {
        var num = parseInt($(".enroll_count").text(),10) || 0 ;
        if ( num  == 0 ) {
            $(".jumbotron-lti-emptySection").show();
        }
    }

    function getSectionUserCount() {
        return $('#people-list li.list-student').length;
    }

    function $getSelectedUsers() {
        return $('#fullClassList input:checked.add-user');
    }

    function getSelectedUserCount() {
        return $getSelectedUsers().length;
    }

    function updateSectionUserCountDisplay() {
        var sectionUserCount = getSectionUserCount();
        $('.enroll_count').text(sectionUserCount);
        $('.enroll_count_pluralize').text(sectionUserCount == 1 ? '' : 's');
    }

    function updateSelectionCountDisplay() {
        var selectedUserCount = getSelectedUserCount();
        $('.selection_count').text(selectedUserCount);
        $('.selection_count_pluralize').text(selectedUserCount == 1 ? '' : 's');
    }

    function loadSectionUsers(msgEleId, msgCSS, msgTxt) {
        $.get(userlistURL, function( data ) {
            $('#sectionUsers').html( data );
            updateSectionUserCountDisplay();
            //call the pagination plugin after the data has been added   
            $('#people-list').alphabetPagination();
            paneHeight();
            // Tooltip message for when removing a user
            $(".icon-removeUser").tooltip();
            $("#people-list").on('click', '.icon-removeUser', removeUser);
        })
        .done(function(){
            //checking for msgCSS and msgTxt controls the displaying from showing when successfully 
            //removing users from a section
            if ( !(typeof msgEleId === 'undefined' || typeof msgCSS === 'undefined' || typeof msgTxt === 'undefined') ) {
                $('li' + msgEleId).removeClass('hidden').html(messageHTML(msgCSS, msgTxt));
            }
        });
    }

    function loadSectionClassList(msgEleId, msgCSS, msgTxt) {
        $.get(classlistURL, function( data ) {     
            $('#fullClassList').html( data );
            // Reset selection count
            updateSelectionCountDisplay();
            $('.btn.add-selected-users').prop('disabled', true);
            // Call the pagination plugin after the data has been added   
            $('#people-in-course').alphabetPagination();
            paneHeight();

            $('#fullClassList input.add-user').on('click', function(){
                updateSelectionCountDisplay();
                $('.btn.add-selected-users').prop('disabled', getSelectedUserCount() <= 0);
            });
        })
        .done(function(){
            //checking for msgCSS and msgTxt controls the displaying from showing when successfully 
            //removing users from a section
            if ( !(typeof msgEleId === 'undefined' || typeof msgCSS === 'undefined' || typeof msgTxt === 'undefined') )
                $('li' + msgEleId).removeClass('hidden').html(messageHTML(msgCSS, msgTxt));

            if ( $("#confirmDelUser").is(":visible") ){
                //hide the popup to signify that is done
                $("#confirmDelUser").modal('hide');
                //make the 'yes, remove and cancel' btn available for clicking
                $('#confirmDelUser button').removeAttr('disabled');
            }
        });
    }

    function showAddUsersPanel() {
        $(this).hide();

        $('#pane-left').removeClass('close-left-pane');
        $('#pane-right').removeClass('close-right-pane');
        $('#pane-left').addClass('slide-left-pane');
        $('#pane-right').addClass('slide-right-pane');

        $(this).addClass('toggle-panes');

        loadSectionClassList();

        paneHeight();

        //to control the rendering of the left and right with mediaqueries
        $('body').addClass('open-user-pane');

        //hide success/error messages when closing the add people pane
        if ( $('.message-holder').is(':visible') )
            $('.message-holder').slideUp(100);
    }

    function hideAddUsersPanel() {
        $('#pane-left').removeClass('slide-left-pane');
        $('#pane-right').removeClass('slide-right-pane');

        $('#pane-left').addClass('close-left-pane');
        $('#pane-right').addClass('close-right-pane');
        $(this).removeClass('toggle-panes');

        $('#pane-container').removeAttr('style');
        //the view can go back to full window
        $('body').removeClass('open-user-pane');

        //hide success/error messages when closing the add people pane
        if ( $('.message-holder').is(':visible') )
            $('.message-holder').slideUp(100);

        $('#addUsers').show();
    }
        
    function removeUser(e) {
        // Prevent the anchor from making the page jump
        e.preventDefault();
        var $removeUserBtn = $(this);
        var userLine = $(this).closest("li");
        var userName = $(this).parent().find(".studentName").text();
        var role = $(this).parent().find(".studentRole").text().trim();
        $('#confirmDelUser .modal-body').html('Remove ' + userName + ' from this section?');
        
        var msgTxt, msgCSS, msgEleId;

        var $modal = $('#confirmDelUser').modal({ keyboard:false });
        $modal.find('#btnConfirmDelUser').on('click', function() {
            //disable the delete popup buttons so the user is not abel to double click
            $('#confirmDelUser button').attr('disabled', 'disabled');
            $.ajax({
                url : rmFromSectionURL, 
                type : "POST",
                data : {
                    user_section_id : $removeUserBtn.attr("id"),
                    section_id: $('main').data('section_id')
                },
                success : function(json) {
                    $("#message-enrollment").fadeOut(2000);
                    userLine.slideUp(500, function(){
                        this.remove();
                    });
                },
                error : function(xhr) {
                    msgEleId = '#message-sectionUsers';
                    msgCSS = 'alert alert-danger';
                    msgTxt = "Error: " + userName + " with role " + role + " has not been deleted from this section.";
                },
                complete: function() {
                    // fetch user data to update alphabet buckets
                    loadSectionUsers(msgEleId, msgCSS, msgTxt);
                    loadSectionClassList();
                }
            })
            .always(function(){
                if ( $('#pane-right').hasClass('close-right-pane') ){
                    $("#confirmDelUser").modal('hide');
                    //make the 'yes, remove and cancel' btn available for clicking
                    $('#confirmDelUser button').removeAttr('disabled');
                }
            });
        });
        $modal.on('hide.bs.modal', function() {
            $modal.find('#btnConfirmDelUser').off('click');
        });
    }

    function addSelectedUsers(e) {
        e.preventDefault();
        var $addSelectedBtn = $(this);
        if ( $('.message-holder').is(':visible') ) {
            $('.message-holder').slideUp(100);
        }

        var usersToAdd = [];
        var userLines = [];
        $getSelectedUsers().each(function(){
            var $checkbox = $(this);
            userLines.push($checkbox.parent());
            usersToAdd.push({
                enrollment_user_id: $checkbox.attr('data-user_id'), 
                enrollment_role: $checkbox.attr('data-enrollment_role'), 
                enrollment_type: $checkbox.attr('data-enrollment_type')
            });
        });

        $('.message-text').empty();
        //overlay a div to prevent the user from fast clicking
        $('#updateOverlay').removeClass('hide').addClass('page-overlay-in');
        $addSelectedBtn.find('i').removeClass('fa-plus').addClass('fa-spinner fa-spin');
        var msgTxt, msgCSS, msgEleId;
        $.ajax({
            url : addToSectionURL, 
            type : "POST",
            data: JSON.stringify({
                section_id: $('main').data('section_id'),
                users_to_add: usersToAdd
            }),
            dataType: 'json',
            contentType: 'application/json',
            success : function(json) {
                var failed_count = json.failed.length;
                msgEleId = '#message-sectionUsers';
                msgTxt = (usersToAdd.length - failed_count) + ' users have been added to this section. ';
                if (failed_count) {
                    msgTxt += failed_count + ' users could not be added to this section.';
                }
                msgCSS = failed_count ? 'alert-warning' : 'alert-success';
                var $userLines = $(userLines).map(function (){return this.toArray();});
                $userLines.slideUp(500, function(){
                    $userLines.remove();
                    hideAddUsersPanel();
                });
            },
            error : function(xhr) {
                msgEleId = '#message-fullClassList';
                msgTxt = 'Error: ' + usersToAdd.length + ' users have not been added to this section.';
                msgCSS = 'alert-danger';
                loadSectionClassList(msgEleId, msgCSS, msgTxt);
            },
            complete: function() {
                loadSectionUsers(msgEleId, msgCSS, msgTxt);
                $addSelectedBtn.find('i').removeClass('fa-spinner fa-spin').addClass('fa fa-plus');
                // Use javascript to pause for half a second so that the fadeout animation has time to finish
                // once the animation is done, we hide the div so user can interact with the page elements
                $('#updateOverlay').removeClass('page-overlay-in').addClass('page-overlay-out').delay(500).queue(function(next){
                    $(this).removeClass('page-overlay-out').addClass('hide').dequeue();
                });
            }
        });
        return false;
    }

    function messageHTML(cssClass, msgToDisplay){
        return '<div class="alert alert-dismissible ' + cssClass + '" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>' +
            '<span class="message-text">' + msgToDisplay + '</span></div>';
    }

    //determine which list higher so that we can have a parent
    //div that shows both lists
    function paneHeight(){
        var leftPane = $('#pane-left').height();
        var rightPane = $('#pane-right').height();
        if (leftPane > rightPane) {
            $('#pane-container').height(leftPane);
        } else {
            $('#pane-container').height(rightPane);
        }
    }

    $('#addUsers').on('click', showAddUsersPanel);
    $('.btn.add-selected-users').on('click', addSelectedUsers);

    // Populate the left pane with section members
    loadSectionUsers();
});

