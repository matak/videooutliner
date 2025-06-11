<?php
// Set headers to allow cross-origin requests
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

// Get the raw POST data
$raw_data = file_get_contents('php://input');

// Define root directory and import directory
$root_dir = dirname(__DIR__); // Go up one level from current script
$import_dir = $root_dir . '/import';

// Get chunk name from URL parameter
$chunk = isset($_GET['chunk']) ? $_GET['chunk'] : null;
if (empty($chunk)) {
    throw new \Exception('Chunk is empty');
}

// Create import directory if it doesn't exist
if (!file_exists($import_dir)) {
    if (!mkdir($import_dir, 0777, true)) {
        throw new \Exception('Chunk is empty');
    }
}

$destination_file = $import_dir . '/' . $chunk . '.srt';

// Check if the received data is an error message
$data = json_decode($raw_data, true);
if (isset($data['error'])) {
    // Save error information to chunk file
    file_put_contents($destination_file, $raw_data);
    throw new \Exception('Error during receiving data, error message');
}

// Validate that we received data
if (empty($raw_data)) {
    throw new \Exception('Error during receiving data, empty data');
}

// Save the response to a file in import directory
if (!file_put_contents($destination_file, $raw_data)) {
    throw new \Exception('Error during saving data');
}

http_response_code(200);
echo json_encode([
    'success' => true,
    'message' => 'Transcription saved successfully',
    'filename' => $destination_file
]); 