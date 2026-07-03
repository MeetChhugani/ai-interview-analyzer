import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('App landing screen smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const InterviewAnalyzerApp());

    // Verify that the dashboard section title is present
    expect(find.text('Choose Category to Start'), findsOneWidget);
  });
}
