import 'dart:ui';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ReportScreen extends StatefulWidget {
  final String sessionId;
  final String category;
  final Map<String, dynamic>? preFetchedReport;

  const ReportScreen({
    super.key,
    required this.sessionId,
    required this.category,
    this.preFetchedReport,
  });

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> with SingleTickerProviderStateMixin {
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  String? _error;
  
  Map<String, dynamic>? _reportData;
  late AnimationController _progressController;

  @override
  void initState() {
    super.initState();
    if (widget.preFetchedReport != null) {
      _reportData = widget.preFetchedReport;
      _isLoading = false;
      _progressController = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1500),
      );
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _progressController.forward();
      });
    } else {
      _progressController = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1500),
      );
      _fetchReport();
    }
  }

  @override
  void dispose() {
    _progressController.dispose();
    super.dispose();
  }

  Future<void> _fetchReport() async {
    try {
      final data = await _apiService.getReport(widget.sessionId);
      if (mounted) {
        setState(() {
          _reportData = data;
          _isLoading = false;
        });
        _progressController.forward();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F4EA),
      body: Stack(
        children: [
          if (_isLoading)
            _buildLoadingIndicator()
          else if (_error != null)
            _buildErrorView()
          else if (_reportData != null)
            _buildReportContent()
        ],
      ),
    );
  }

  Widget _buildLoadingIndicator() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(
            color: Color(0xFF0D3A31),
            strokeWidth: 3,
          ),
          SizedBox(height: 16),
          Text(
            'Analyzing recordings & compiling metrics...',
            style: TextStyle(color: Color(0xFF5A6561), fontSize: 14),
          )
        ],
      ),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded, color: Colors.redAccent, size: 60),
            const SizedBox(height: 16),
            const Text(
              'Failed to Generate Report',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: Color(0xFF0D3A31)),
            ),
            const SizedBox(height: 8),
            Text(
              _error ?? 'An unknown error occurred.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF5A6561)),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0D3A31),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
              child: const Text('Back to Dashboard'),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildReportContent() {
    final breakdown = _reportData!['scores_breakdown'] as Map<String, dynamic>;
    final overall = _reportData!['overall_score'] as int;
    final metrics = _reportData!['metrics'] as Map<String, dynamic>;
    final feedback = _reportData!['feedback'] as List<dynamic>;
    final qEvals = _reportData!['question_evaluations'] as List<dynamic>?;

    return SafeArea(
      child: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          // Header
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      GestureDetector(
                        onTap: () => Navigator.of(context).pushNamedAndRemoveUntil('/home', (route) => false),
                        child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
                          ),
                          child: const Icon(Icons.arrow_back_rounded, color: Color(0xFF0D3A31)),
                        ),
                      ),
                      const SizedBox(width: 14),
                      const Text(
                        'Evaluation Report',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 22,
                          color: Color(0xFF0D3A31),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Category: ${widget.category}',
                    style: const TextStyle(color: Color(0xFF5A6561), fontSize: 14, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
          ),

          // Scores Card (Radial Ring + Mini Bars)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: Container(
                padding: const EdgeInsets.all(24.0),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
                ),
                child: Row(
                  children: [
                    // Radial Gauge
                    _buildOverallRing(overall),
                    const SizedBox(width: 24),
                    // Breakdown details
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildBreakdownBar('Speech Clarity', (breakdown['speech_clarity'] ?? 0) as int, const Color(0xFF8B5CF6)),
                          const SizedBox(height: 12),
                          _buildBreakdownBar('Confidence', (breakdown['confidence'] ?? 0) as int, const Color(0xFF0D3A31)),
                          const SizedBox(height: 12),
                          _buildBreakdownBar('Eye Contact', (breakdown['eye_contact'] ?? 0) as int, const Color(0xFFD8B28A)),
                          const SizedBox(height: 12),
                          _buildBreakdownBar('Engagement', (breakdown['engagement'] ?? 0) as int, const Color(0xFFE5B595)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Core Metrics Grid
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.only(left: 24.0, right: 24.0, top: 24.0),
              child: GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.5,
                children: [
                  _buildMetricStatCard('Speaking Pace', '${metrics['wpm']} WPM', Icons.speed_rounded, const Color(0xFF0D3A31)),
                  _buildMetricStatCard('Eye Contact', '${((metrics['eye_contact_ratio'] as double) * 100).toInt()}%', Icons.visibility_rounded, const Color(0xFFD8B28A)),
                  _buildMetricStatCard('Posture Score', '${(metrics['average_posture'] as double).toInt()}%', Icons.accessibility_new_rounded, const Color(0xFFE5B595)),
                  _buildMetricStatCard('Filler Words', '${metrics['filler_words_total']}', Icons.format_quote_rounded, const Color(0xFF8B5CF6)),
                ],
              ),
            ),
          ),

          // AI Coach Card
          if (_reportData!['ai_coaching_summary'] != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.only(left: 24.0, right: 24.0, top: 24.0),
                child: _buildAiCoachCard(_reportData!['ai_coaching_summary'] as String),
              ),
            ),

          // Response Quality Trend Chart
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 24.0),
              child: Container(
                height: 250,
                padding: const EdgeInsets.only(top: 20, bottom: 12, right: 20, left: 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(left: 14.0, bottom: 16),
                      child: Text(
                        'Response Quality Trend',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF0D3A31)),
                      ),
                    ),
                    Expanded(
                      child: _buildTimelineChart(qEvals),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Question Breakdown Section Header
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.only(left: 24.0, right: 24.0, top: 10.0, bottom: 12.0),
              child: const Text(
                'Question & Answer Analysis',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF0D3A31),
                ),
              ),
            ),
          ),

          // Question Breakdown Cards
          if (qEvals != null && qEvals.isNotEmpty)
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final eval = qEvals[index];
                    final score = eval['quality_score'] as int? ?? 0;
                    final question = eval['question'] as String? ?? '';
                    final answer = eval['user_answer'] as String? ?? '';
                    final qFeedback = eval['feedback'] as String? ?? '';
                    final idealAnswer = eval['ideal_answer'] as String? ?? '';
                    final correctnessScore = eval['correctness_score'] as int? ?? score;
                    final correctnessFeedback = eval['correctness_feedback'] as String? ?? '';

                    Color scoreColor = const Color(0xFF0D3A31);
                    if (correctnessScore < 55) {
                      scoreColor = Colors.redAccent;
                    } else if (correctnessScore < 80) {
                      scoreColor = const Color(0xFFD8B28A);
                    }

                    return Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  question,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                    color: Color(0xFF0D3A31),
                                    height: 1.35,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: scoreColor.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  '$correctnessScore%',
                                  style: TextStyle(
                                    color: scoreColor,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'Your Answer:',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.black38),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            answer.isEmpty ? "(No answer spoken)" : answer,
                            style: const TextStyle(
                              fontSize: 13,
                              fontStyle: FontStyle.italic,
                              color: Color(0xFF5A6561),
                              height: 1.4,
                            ),
                          ),
                          // Ideal Answer Card
                          if (idealAnswer.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFAF7F0), // cream
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Row(
                                    children: [
                                      Icon(Icons.vpn_key_rounded, color: Color(0xFFD8B28A), size: 16),
                                      SizedBox(width: 8),
                                      Text(
                                        'Ideal Answer Key:',
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF0D3A31)),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    idealAnswer,
                                    style: const TextStyle(
                                      fontSize: 12.5,
                                      color: Color(0xFF5A6561),
                                      height: 1.45,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0D3A31).withOpacity(0.04),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.1)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.tips_and_updates_rounded, color: Color(0xFFD8B28A), size: 18),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'AI Grading Match:',
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF0D3A31)),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        correctnessFeedback.isNotEmpty ? correctnessFeedback : qFeedback,
                                        style: const TextStyle(
                                          color: Color(0xFF5A6561),
                                          fontSize: 12.5,
                                          height: 1.4,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                  childCount: qEvals.length,
                ),
              ),
            )
          else
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 24.0, vertical: 10),
                child: Text('No question responses recorded.', style: TextStyle(color: Colors.black38)),
              ),
            ),

          // Feedback list with expand/collapse
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: const Text(
                'Personalized Coach Insights',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF0D3A31),
                ),
              ),
            ),
          ),

          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12.0),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final item = feedback[index];
                  return _buildFeedbackAccordion(item);
                },
                childCount: feedback.length,
              ),
            ),
          ),

          // Finish CTA
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.only(left: 24.0, right: 24.0, top: 30.0, bottom: 60.0),
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pushNamedAndRemoveUntil('/home', (route) => false),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: const Color(0xFF0D3A31),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                  elevation: 0,
                ),
                child: const Text(
                  'RETURN TO DASHBOARD',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, letterSpacing: 1.5),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _getQualitativeLabel(int score) {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    return 'Needs Improvement';
  }

  Color _getQualitativeColor(int score) {
    if (score >= 80) return const Color(0xFF0D3A31);
    if (score >= 60) return const Color(0xFFD8B28A);
    return Colors.redAccent;
  }

  Widget _buildOverallRing(int overall) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedBuilder(
          animation: _progressController,
          builder: (context, child) {
            final animatedScore = (_progressController.value * overall).toInt();
            return SizedBox(
              width: 100,
              height: 100,
              child: Stack(
                children: [
                  Positioned.fill(
                    child: CircularProgressIndicator(
                      value: _progressController.value * (overall / 100.0),
                      strokeWidth: 8,
                      backgroundColor: const Color(0xFF0D3A31).withOpacity(0.08),
                      valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF0D3A31)),
                    ),
                  ),
                  Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '$animatedScore%',
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF0D3A31),
                          ),
                        ),
                        const Text(
                          'OVERALL',
                          style: TextStyle(
                            fontSize: 8,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF5A6561),
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                  )
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: _getQualitativeColor(overall).withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: _getQualitativeColor(overall).withOpacity(0.3)),
          ),
          child: Text(
            _getQualitativeLabel(overall),
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.bold,
              color: _getQualitativeColor(overall),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBreakdownBar(String label, int score, Color barColor) {
    return AnimatedBuilder(
      animation: _progressController,
      builder: (context, child) {
        final animatedProgress = _progressController.value * (score / 100.0);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0D3A31)),
                ),
                Text(
                  '${(animatedProgress * 100).toInt()}%',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: barColor),
                ),
              ],
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: animatedProgress,
                backgroundColor: barColor.withOpacity(0.08),
                valueColor: AlwaysStoppedAnimation<Color>(barColor),
                minHeight: 6,
              ),
            )
          ],
        );
      },
    );
  }

  Widget _buildMetricStatCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF5A6561)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: Color(0xFF0D3A31)),
          ),
        ],
      ),
    );
  }

  Widget _buildAiCoachCard(String text) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0D3A31).withOpacity(0.02),
            blurRadius: 10,
            spreadRadius: 1,
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.psychology_outlined, color: Color(0xFF0D3A31), size: 24),
              SizedBox(width: 10),
              Text(
                'AI INTERVIEW COACH',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: Color(0xFF0D3A31),
                  letterSpacing: 1.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            text,
            style: const TextStyle(
              color: Color(0xFF5A6561),
              fontSize: 13,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineChart(List<dynamic>? qEvals) {
    if (qEvals == null || qEvals.isEmpty) {
      return const Center(child: Text('No response trend data available', style: TextStyle(color: Colors.black38)));
    }

    List<FlSpot> spots = [];
    for (int i = 0; i < qEvals.length; i++) {
      final score = (qEvals[i]['quality_score'] as num?)?.toDouble() ?? 0.0;
      spots.add(FlSpot(i.toDouble(), score));
    }

    if (spots.isEmpty) {
      spots = [const FlSpot(0, 0), const FlSpot(1, 0)];
    }

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (value) {
            return FlLine(
              color: const Color(0xFF0D3A31).withOpacity(0.05),
              strokeWidth: 1,
            );
          },
        ),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 22,
              interval: 1,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx >= 0 && idx < qEvals.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 4.0),
                    child: Text('Q${idx + 1}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF5A6561))),
                  );
                }
                return const SizedBox();
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 20,
              getTitlesWidget: (value, meta) {
                return Text('${value.toInt()}%', style: const TextStyle(fontSize: 9, color: Color(0xFF5A6561)));
              },
              reservedSize: 32,
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: spots.length > 1 ? spots.length.toDouble() - 1 : 1.0,
        minY: 0,
        maxY: 100,
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: const Color(0xFF0D3A31),
            barWidth: 3.5,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: true),
            belowBarData: BarAreaData(
              show: true,
              color: const Color(0xFF0D3A31).withOpacity(0.06),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFeedbackAccordion(dynamic item) {
    final category = item['category'] as String;
    final status = item['status'] as String;
    final score = item['score'] as int;
    final detail = item['detail'] as String;

    Color themeColor = const Color(0xFF0D3A31);
    IconData icon = Icons.info_outline_rounded;
    if (status == 'Critical') {
      themeColor = Colors.redAccent;
      icon = Icons.cancel_outlined;
    } else if (status == 'Needs Improvement') {
      themeColor = const Color(0xFFD8B28A);
      icon = Icons.warning_amber_rounded;
    } else if (status == 'Good') {
      themeColor = const Color(0xFF10B981);
      icon = Icons.check_circle_outline_rounded;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
      ),
      child: ExpansionTile(
        leading: Icon(icon, color: themeColor),
        title: Text(
          category,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF0D3A31)),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: themeColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            '$score%',
            style: TextStyle(
              color: themeColor,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 20.0, right: 20.0, bottom: 20.0, top: 4.0),
            child: Text(
              detail,
              style: const TextStyle(color: Color(0xFF5A6561), fontSize: 13, height: 1.45),
            ),
          ),
        ],
      ),
    );
  }
}
