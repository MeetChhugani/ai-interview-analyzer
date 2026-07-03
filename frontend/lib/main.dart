import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'services/profile_store.dart';
import 'screens/onboarding_screen.dart';
import 'screens/home_screen.dart';
import 'screens/interview_screen.dart';
import 'screens/report_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final profile = await ProfileStore.loadProfile();
  runApp(InterviewAnalyzerApp(hasProfile: profile != null));
}

class InterviewAnalyzerApp extends StatelessWidget {
  final bool hasProfile;
  const InterviewAnalyzerApp({super.key, required this.hasProfile});

  @override
  Widget build(BuildContext context) {
    final themeData = ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: const Color(0xFFF8F4EA), // Warm light cream
      primaryColor: const Color(0xFF0D3A31), // Forest green
      colorScheme: const ColorScheme.light(
        primary: Color(0xFF0D3A31),
        secondary: Color(0xFFD8B28A), // Warm gold
        surface: Colors.white,
        background: Color(0xFFF8F4EA),
        error: Color(0xFFBA1A1A),
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: Color(0xFF0D3A31),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(
            color: Color(0xFFFAF7F0),
            width: 1,
          ),
        ),
      ),
      textTheme: GoogleFonts.plusJakartaSansTextTheme(
        ThemeData.light().textTheme.apply(
              bodyColor: const Color(0xFF1E2522), // Off-black
              displayColor: const Color(0xFF0D3A31), // Deep green
            ),
      ),
      useMaterial3: true,
    );

    return MaterialApp(
      title: 'AI Smart Interview Analyzer',
      debugShowCheckedModeBanner: false,
      theme: themeData,
      initialRoute: hasProfile ? '/home' : '/',
      routes: {
        '/': (context) => const OnboardingScreen(),
        '/home': (context) => const HomeScreen(),
      },
      onGenerateRoute: (settings) {
        if (settings.name == '/interview') {
          final args = settings.arguments as Map<String, dynamic>;
          return MaterialPageRoute(
            builder: (context) => InterviewScreen(
              sessionId: args['sessionId'] as String,
              category: args['category'] as String,
              questions: args['questions'] as List<String>,
            ),
          );
        } else if (settings.name == '/report') {
          final args = settings.arguments as Map<String, dynamic>;
          return MaterialPageRoute(
            builder: (context) => ReportScreen(
              sessionId: args['sessionId'] as String,
              category: args['category'] as String,
            ),
          );
        }
        return null;
      },
    );
  }
}
