import 'dart:convert';
import 'dart:io' show File;
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiService {
  // Static variable to store the server IP/host (e.g., "127.0.0.1:8000" or "192.168.1.15:8000")
  static String serverIp = '127.0.0.1:8000';

  // Determine backend URL based on device running the application
  static String get _defaultBaseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000/api';
    }
    String cleanIp = serverIp.replaceAll('http://', '').replaceAll('https://', '');
    return 'http://$cleanIp/api';
  }

  final String? _customBaseUrl;
  String get baseUrl => _customBaseUrl ?? _defaultBaseUrl;

  ApiService({String? baseUrl}) : _customBaseUrl = baseUrl;

  /// Starts a new evaluation session for a specific job category.
  Future<Map<String, dynamic>> createSession(String category, {List<String>? customQuestions}) async {
    final url = Uri.parse('$baseUrl/session');
    try {
      final body = {
        'category': category,
        if (customQuestions != null) 'custom_questions': customQuestions,
      };
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to start session: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error starting session: $e');
    }
  }

  /// Sends a single camera frame snapshot (JPEG) to the server for visual behavioral analysis.
  Future<Map<String, dynamic>> sendFrame(String sessionId, List<int> imageBytes) async {
    final url = Uri.parse('$baseUrl/session/$sessionId/frame');
    try {
      final request = http.MultipartRequest('POST', url)
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            imageBytes,
            filename: 'frame.jpg',
          ),
        );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to upload frame: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error uploading frame: $e');
    }
  }

  /// Uploads an audio clip representing a section of the user's speech.
  Future<Map<String, dynamic>> sendAudio(String sessionId, String audioFilePath, double durationSeconds, int questionIndex) async {
    final url = Uri.parse('$baseUrl/session/$sessionId/audio');
    try {
      final request = http.MultipartRequest('POST', url)
        ..fields['duration'] = durationSeconds.toString()
        ..fields['question_index'] = questionIndex.toString();

      if (kIsWeb) {
        // On Web, audioFilePath is a blob URL. We must fetch the bytes from this local URL.
        final blobResponse = await http.get(Uri.parse(audioFilePath));
        final bytes = blobResponse.bodyBytes;
        request.files.add(
          http.MultipartFile.fromBytes(
            'file',
            bytes,
            filename: 'audio.wav',
          ),
        );
      } else {
        final file = File(audioFilePath);
        if (!await file.exists()) {
          throw Exception('Audio file not found at path: $audioFilePath');
        }
        request.files.add(await http.MultipartFile.fromPath('file', audioFilePath));
      }

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to upload audio: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error uploading audio: $e');
    }
  }

  /// Fetches the final accumulated scoring report, timeline charts, and actionable improvement tips.
  Future<Map<String, dynamic>> getReport(String sessionId) async {
    final url = Uri.parse('$baseUrl/session/$sessionId/report');
    try {
      final response = await http.get(url);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to retrieve session report: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error fetching report: $e');
    }
  }
}
