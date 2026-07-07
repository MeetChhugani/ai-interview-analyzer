import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class AuthStore {
  static Map<String, dynamic>? _cachedUser;

  static Future<File> get _authFile async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/auth_user.json');
  }

  static Future<Map<String, dynamic>?> getAuthUser() async {
    if (_cachedUser != null) return _cachedUser;
    try {
      final file = await _authFile;
      if (await file.exists()) {
        final content = await file.readAsString();
        _cachedUser = jsonDecode(content);
        return _cachedUser;
      }
    } catch (_) {}
    return null;
  }

  static Future<void> saveAuthUser(Map<String, dynamic> user) async {
    _cachedUser = user;
    try {
      final file = await _authFile;
      await file.writeAsString(jsonEncode(user));
    } catch (_) {}
  }

  static Future<void> clearAuthUser() async {
    _cachedUser = null;
    try {
      final file = await _authFile;
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {}
  }

  static Future<bool> isLoggedIn() async {
    final user = await getAuthUser();
    return user != null && user['id'] != null;
  }
}
