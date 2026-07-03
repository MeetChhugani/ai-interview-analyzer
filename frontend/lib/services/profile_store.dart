import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class ProfileStore {
  static Map<String, dynamic>? _cachedProfile;
  static List<Map<String, dynamic>>? _cachedHistory;

  static Future<File> get _profileFile async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/user_profile.json');
  }

  static Future<File> get _historyFile async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/interview_history.json');
  }

  static Future<Map<String, dynamic>?> loadProfile() async {
    if (_cachedProfile != null) return _cachedProfile;
    try {
      final file = await _profileFile;
      if (await file.exists()) {
        final content = await file.readAsString();
        _cachedProfile = jsonDecode(content);
        return _cachedProfile;
      }
    } catch (_) {}
    return null;
  }

  static Future<void> saveProfile(Map<String, dynamic> profile) async {
    _cachedProfile = profile;
    try {
      final file = await _profileFile;
      await file.writeAsString(jsonEncode(profile));
    } catch (_) {}
  }

  static Future<void> clearProfile() async {
    _cachedProfile = null;
    try {
      final file = await _profileFile;
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {}
  }

  static Future<List<Map<String, dynamic>>> loadHistory() async {
    if (_cachedHistory != null) return _cachedHistory!;
    try {
      final file = await _historyFile;
      if (await file.exists()) {
        final content = await file.readAsString();
        final List<dynamic> list = jsonDecode(content);
        _cachedHistory = list.cast<Map<String, dynamic>>();
        return _cachedHistory!;
      }
    } catch (_) {}
    return [];
  }

  static Future<void> saveHistoryItem(Map<String, dynamic> item) async {
    final history = await loadHistory();
    history.insert(0, item);
    _cachedHistory = history;
    try {
      final file = await _historyFile;
      await file.writeAsString(jsonEncode(history));
    } catch (_) {}
  }

  static Future<void> clearHistory() async {
    _cachedHistory = [];
    try {
      final file = await _historyFile;
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {}
  }
}
