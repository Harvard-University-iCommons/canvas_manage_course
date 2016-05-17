(function() {
    function openContentLink(event) {
        // only forward click() to a.content-link if the link itself was not
        // the target of the original click, to avoid firing multiple clicks
        if (!$(event.target).hasClass('content-link')) {
            // forward click() to embedded link after disabling redundant clicks
            $(this).off('click').find('a.content-link')[0].click();
        }
    }
    // 'disabled' cards have no links, so no window location change
    $('.card-body').on('click', openContentLink);
})();
