// Open modal function accepting a callback
function openPortsModal(callback) {
	// Reset form fields
	$('#addPortForm')[0].reset();
	$('#portsModal').modal('show');
    $('#portsModal').on('shown.bs.modal', function () {
        $('#port_input').focus();
    });
	
	// Set up save button click
	$('#savePortBtn').off('click').on('click', function() {
		// Construct IP from the four inputs
		var port = $('#port_input').val();
		
		$('#portsModal').modal('hide');
		if (callback && typeof callback === 'function') {
			callback(port);
		}
	});

    $('#port_input').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            $(this).blur();
            $('#savePortBtn').click();
        } else if (e.key === '.') {
            e.preventDefault();
        }
    });
}
