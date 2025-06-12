<?php
// Set headers to allow cross-origin requests
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

// Define root directory and import directory
$root_dir = dirname(__DIR__); // Go up one level from current script
$import_dir = realpath($root_dir . '/import');


// Get the raw POST data
$raw_data = file_get_contents('php://input');

// Get chunk name from URL parameter
$chunk = isset($_GET['chunk']) ? $_GET['chunk'] : null;
if (empty($chunk)) {
    throw new \Exception('Chunk is empty');
}

// Create import directory if it doesn't exist
if (!file_exists($import_dir)) {
    if (!mkdir($import_dir, 0777, true)) {
        throw new \Exception('Import directory not found');
    }
}

$destination_file = $import_dir . '/' . $chunk . '.srt';
$log_file = $import_dir . '/' . $chunk . '.srt.log';

// Detect encoding of the raw data
$encoding = mb_detect_encoding($raw_data, ['UTF-8', 'ASCII', 'ISO-8859-1', 'Windows-1252'], true);

$log_message = date('Y-m-d H:i:s') . " - Chunk: $chunk - Encoding: " . ($encoding ?: 'Unknown') . "\n";
$log_message .= "Raw data: " . $raw_data . "\n";
$log_message .= "----------------------------------------\n";
file_put_contents($log_file, $log_message, FILE_APPEND);


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

// Remove quotes and convert \n to actual newlines
$content = trim($raw_data, '"');
$content = str_replace('\n', "\n", $content);

// Save the response to a file in import directory
if (!file_put_contents($destination_file, $content)) {
    throw new \Exception('Error during saving data');
}

http_response_code(200);
echo json_encode([
    'success' => true,
    'message' => 'Transcription saved successfully',
    'filename' => $destination_file
]); 