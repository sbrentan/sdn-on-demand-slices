async function send_packet(packet_info){
    result = await fetchData(`${ApiPaths.SEND_PACKET}`, 'POST', packet_info)
    packet_id = result['packet_id']

    // in loop, check if packet result is avaialble
    packet_result = null
    while(true){
        result = await fetchData(`${ApiPaths.PACKET_RESULT.replace("{packet_id}", packet_id)}`, 'GET')
        if(result['status'] == 'completed'){
            packet_result = result
            break
        }
        await new Promise(r => setTimeout(r, 300));
    }

    if (packet_result != null){
        animatePacketPath(packet_result["steps"])
    }
}

function openSendPacketModal(callback) {
	// Reset form fields
	$('#sendPacketForm')[0].reset();
	$('#sendPacketModal').modal('show');

	// on modal show, focus on the first input
	$('#sendPacketModal').on('shown.bs.modal', function() {
		$('#packet-protocol_select').focus();
	});

    // reset select options
    $('#packet-source_select').empty();
    $('#packet-dest_select').empty();

    $('#packet-source_select').append($('<option>', {
        value: '',
        text: '--- Select Source Host ---',
        disabled: true,
        selected: true
    }));

    $('#packet-dest_select').append($('<option>', {
        value: '',
        text: '--- Select Destination Host ---',
        disabled: true,
        selected: true
    }));

    // Reset port visibility
    document.getElementById("packet-dst_port_input").style.display = "none";
    document.getElementById("packet-src_port_input").style.display = "none";

    // Load data in host source and destination from graph_data
    ordered_data_nodes = graph_data.nodes.sort((a, b) => a.name.localeCompare(b.name))
    ordered_data_nodes.forEach(element => {
        if (element.type === 'Host') {
            $('#packet-source_select').append($('<option>', {
                value: element.id,
                text: element.name
            }));
            $('#packet-dest_select').append($('<option>', {
                value: element.id,
                text: element.name
            }));
        }
    });
    
	
	// Set up save button click
	$('#sendPacketBtn').off('click').on('click', function() {

        var protocol = $('#packet-protocol_select').val();
		if (protocol === '' || protocol === null || protocol === undefined) {
			alert('Please select a protocol.');
			return;
		}
		var protocol = $('#packet-protocol_select').val();

        var dst_port = 0;
        if (protocol === 'TCP' || protocol === 'UDP') {
            dst_port = $('#packet-dst_port_input').val();
            if (dst_port === '' || isNaN(dst_port) || dst_port < 1 || dst_port > 65535) {
                alert('Please enter a valid source port number between 1 and 65535.');
                return;
            }
            dst_port = $('#packet-dst_port_input').val();
        }

		var src_port = $('#packet-src_port_input').val();
        if (src_port === '') {
            src_port = null;
        } else {
            if (isNaN(src_port) || src_port < 1 || src_port > 65535) {
                alert('Please enter a valid source port number between 1 and 65535.');
                return;
            }
            src_port = $('#packet-src_port_input').val();
        }

        var source = $('#packet-source_select').val();
        if (source === '' || source === null || source === undefined) {
            alert('Please select a source host.');
            return;
        }

        var dest = $('#packet-dest_select').val();
        if (dest === '' || dest === null || dest === undefined) {
            alert('Please select a destination host.');
            return;
        }

        packet_info = {
            "source": source,
            "dest": dest,
            "protocol": protocol
        }
        if (src_port != null)
            packet_info['src_port'] = src_port
        if (dst_port != null)
            packet_info['dst_port'] = dst_port

        console.log(packet_info)
		
		$('#sendPacketModal').modal('hide');
        send_packet(packet_info)
	});
}

document.addEventListener('DOMContentLoaded', function() {
    // add event listener to send packet button
    document.getElementById('send-packet-btn')?.addEventListener('click', function() {
        openSendPacketModal();
    });
});