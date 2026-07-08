import 'dart:async';
import 'dart:ui';
import 'dart:io';
import 'dart:math' as math;
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../services/api_service.dart';
import '../services/profile_store.dart';

enum InterviewUIStatus { active, analyzing, completed }

class InterviewScreen extends StatefulWidget {
  final String sessionId;
  final String category;
  final List<String> questions;

  const InterviewScreen({
    super.key,
    required this.sessionId,
    required this.category,
    required this.questions,
  });

  @override
  State<InterviewScreen> createState() => _InterviewScreenState();
}

class _InterviewScreenState extends State<InterviewScreen> with TickerProviderStateMixin {
  final ApiService _apiService = ApiService();
  CameraController? _cameraController;
  final AudioRecorder _audioRecorder = AudioRecorder();
  
  bool _isCameraInitialized = false;
  bool _isRecording = false;
  int _currentQuestionIndex = 0;
  
  int _secondsElapsed = 0;
  Timer? _sessionTimer;
  Timer? _frameUploadTimer;
  Timer? _audioUploadTimer;

  // Text to speech parameters
  FlutterTts? _flutterTts;
  Timer? _ttsBackupTimer;
  bool _isVoiceRecordingActive = false;
  bool _isSpeakingModeActive = false;

  // Real-time HUD and Alert states
  String? _currentAlert;
  Color _hudColor = const Color(0xFF0D3A31); // Forest green default
  bool _faceDetected = true;
  bool _eyeContact = true;
  int _postureScore = 100;
  String _emotion = 'confident';
  double _waveformAmplitude = 0.1;
  StreamSubscription<Amplitude>? _amplitudeSubscription;

  // UI state
  InterviewUIStatus _uiStatus = InterviewUIStatus.active;
  Map<String, dynamic>? _finalReportData;
  double _analyzingProgress = 0.0;
  Timer? _analyzingTimer;

  // Animation controllers
  late AnimationController _hudPulseController;
  late AnimationController _alertController;
  late AnimationController _waveformController;

  void _cancelTtsBackupTimer() {
    _ttsBackupTimer?.cancel();
    _ttsBackupTimer = null;
  }

  @override
  void initState() {
    super.initState();
    _initInterviewApp();

    _hudPulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _alertController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );

    _waveformController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    )..repeat();
  }

  @override
  void dispose() {
    _sessionTimer?.cancel();
    _frameUploadTimer?.cancel();
    _audioUploadTimer?.cancel();
    _analyzingTimer?.cancel();
    _amplitudeSubscription?.cancel();
    _ttsBackupTimer?.cancel();
    _cameraController?.dispose();
    _audioRecorder.dispose();
    _flutterTts?.stop();
    _hudPulseController.dispose();
    _alertController.dispose();
    _waveformController.dispose();
    super.dispose();
  }

  Future<void> _initInterviewApp() async {
    // 1. Initialize Camera
    try {
      final cameras = await availableCameras();
      if (cameras.isNotEmpty) {
        final frontCamera = cameras.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
          orElse: () => cameras.first,
        );

        _cameraController = CameraController(
          frontCamera,
          ResolutionPreset.medium,
          enableAudio: false,
        );

        await _cameraController!.initialize();
        if (mounted) {
          setState(() {
            _isCameraInitialized = true;
          });
        }
      }
    } catch (e) {
      debugPrint("Camera initialization error: $e");
    }

    _startTimers();
    _initTts();
  }

  Future<void> _initTts() async {
    try {
      _flutterTts = FlutterTts();
      await _flutterTts!.setLanguage("en-US");
      await _flutterTts!.setSpeechRate(0.45);
      await _flutterTts!.setVolume(1.0);
      await _flutterTts!.setPitch(1.0);
      
      _flutterTts!.setStartHandler(() {
        _stopRecordingForQuestion();
      });
      _flutterTts!.setCompletionHandler(() {
        _cancelTtsBackupTimer();
      });
      _flutterTts!.setErrorHandler((msg) {
        _cancelTtsBackupTimer();
      });
      
      if (widget.questions.isNotEmpty) {
        _speakQuestion(widget.questions[0]);
      }
    } catch (e) {
      _cancelTtsBackupTimer();
    }
  }

  Future<void> _speakQuestion(String text) async {
    if (_flutterTts == null) return;
    try {
      _cancelTtsBackupTimer();
      await _flutterTts!.stop();
      
      int estimatedSeconds = (text.length / 14).ceil() + 2;
      if (estimatedSeconds < 3) estimatedSeconds = 3;
      if (estimatedSeconds > 15) estimatedSeconds = 15;
      
      _ttsBackupTimer = Timer(Duration(seconds: estimatedSeconds), () {
        // Backup timer complete
      });

      await _flutterTts!.speak(text);
    } catch (e) {
      _cancelTtsBackupTimer();
    }
  }

  void _startTimers() {
    _isRecording = true;
    _sessionTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted && _uiStatus == InterviewUIStatus.active) {
        setState(() {
          _secondsElapsed++;
        });
      }
    });

    _frameUploadTimer = Timer.periodic(const Duration(milliseconds: 700), (timer) {
      if (_uiStatus == InterviewUIStatus.active) {
        _captureAndUploadFrame();
      }
    });
  }

  Future<void> _captureAndUploadFrame() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    try {
      final XFile pictureFile = await _cameraController!.takePicture();
      final bytes = await pictureFile.readAsBytes();
      
      try {
        await File(pictureFile.path).delete();
      } catch (_) {}

      final response = await _apiService.sendFrame(widget.sessionId, bytes);
      
      if (mounted && _uiStatus == InterviewUIStatus.active) {
        setState(() {
          _faceDetected = response['face_detected'] ?? true;
          _eyeContact = response['eye_contact'] ?? true;
          _postureScore = response['posture_score'] ?? 100;
          _emotion = response['dominant_emotion'] ?? 'confident';
          
          _hudColor = _faceDetected 
              ? (_eyeContact ? const Color(0xFF0D3A31) : const Color(0xFFD8B28A)) 
              : Colors.redAccent;
          
          final alert = response['alert'];
          if (alert != null && alert.isNotEmpty) {
            _currentAlert = alert;
            _alertController.forward();
            Timer(const Duration(seconds: 3), () {
              if (mounted && _currentAlert == alert) {
                _alertController.reverse().then((_) {
                  setState(() {
                    _currentAlert = null;
                  });
                });
              }
            });
          }
        });
      }
    } catch (_) {}
  }

  Future<void> _startRecordingForQuestion() async {
    if (!mounted || !_isRecording) return;
    if (!_isSpeakingModeActive) return;
    if (_isVoiceRecordingActive) return;
    _isVoiceRecordingActive = true;
    
    try {
      if (await _audioRecorder.hasPermission()) {
        if (await _audioRecorder.isRecording()) {
          await _audioRecorder.stop();
        }
        
        final tempDir = await getTemporaryDirectory();
        
        _amplitudeSubscription = _audioRecorder
            .onAmplitudeChanged(const Duration(milliseconds: 80))
            .listen((amp) {
              if (mounted) {
                setState(() {
                  _waveformAmplitude = ((amp.current + 50) / 50).clamp(0.05, 1.0);
                });
              }
            });

        final initFileName = 'chunk_init_${DateTime.now().millisecondsSinceEpoch}.wav';
        final initFilePath = '${tempDir.path}/$initFileName';
        await _audioRecorder.start(
          const RecordConfig(encoder: AudioEncoder.wav), 
          path: initFilePath
        );

        _audioUploadTimer?.cancel();
        _audioUploadTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
          if (!_isRecording) return;
          
          final path = await _audioRecorder.stop();
          if (path != null) {
            _apiService.sendAudio(widget.sessionId, path, 5.0, _currentQuestionIndex).catchError((e) {
              return <String, dynamic>{};
            });
          }
          
          final nextFileName = 'chunk_${DateTime.now().millisecondsSinceEpoch}.wav';
          final nextFilePath = '${tempDir.path}/$nextFileName';
          await _audioRecorder.start(
            const RecordConfig(encoder: AudioEncoder.wav), 
            path: nextFilePath
          );
        });
      }
    } catch (_) {
      _isVoiceRecordingActive = false;
    }
  }

  Future<void> _stopRecordingForQuestion() async {
    _isVoiceRecordingActive = false;
    _audioUploadTimer?.cancel();
    _amplitudeSubscription?.cancel();
    try {
      if (await _audioRecorder.isRecording()) {
        await _audioRecorder.stop();
      }
      if (mounted) {
        setState(() {
          _waveformAmplitude = 0.05;
        });
      }
    } catch (_) {}
  }

  Future<void> _triggerChunkUploadAndNext() async {
    final activeIndex = _currentQuestionIndex;
    _audioUploadTimer?.cancel();
    _amplitudeSubscription?.cancel();
    
    if (_isSpeakingModeActive) {
      final path = await _audioRecorder.stop();
      if (path != null) {
        _apiService.sendAudio(widget.sessionId, path, 5.0, activeIndex).catchError((e) {
          return <String, dynamic>{};
        });
      }
    }

    setState(() {
      _currentQuestionIndex++;
      _isSpeakingModeActive = false; // Reset speaking mode for the next question
      _isVoiceRecordingActive = false; // Reset voice recording flag
      _waveformAmplitude = 0.05; // Flatline waveform visualizer
    });

    if (_currentQuestionIndex < widget.questions.length) {
      _speakQuestion(widget.questions[_currentQuestionIndex]);
    }
  }

  Future<void> _endInterview() async {
    _audioUploadTimer?.cancel();
    _amplitudeSubscription?.cancel();
    if (_isSpeakingModeActive) {
      final path = await _audioRecorder.stop();
      if (path != null) {
        _apiService.sendAudio(widget.sessionId, path, 5.0, _currentQuestionIndex).catchError((e) {
          return <String, dynamic>{};
        });
      }
    }

    setState(() {
      _isRecording = false;
      _isSpeakingModeActive = false;
      _isVoiceRecordingActive = false; // Reset voice recording flag
      _waveformAmplitude = 0.05; // Flatline waveform visualizer
      _uiStatus = InterviewUIStatus.analyzing;
    });
    
    _sessionTimer?.cancel();
    _frameUploadTimer?.cancel();
    _audioUploadTimer?.cancel();
    _amplitudeSubscription?.cancel();
    
    try {
      _flutterTts?.stop();
      await _audioRecorder.stop();
    } catch (_) {}

    // Mock progress loading timer
    _analyzingTimer = Timer.periodic(const Duration(milliseconds: 150), (timer) {
      if (mounted) {
        setState(() {
          if (_analyzingProgress < 0.9) {
            _analyzingProgress += 0.05;
          }
        });
      }
    });

    await Future.delayed(const Duration(seconds: 2));

    try {
      final reportData = await _apiService.getReport(widget.sessionId);
      
      // Save report metadata locally
      final monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      final dateStr = '${monthNames[DateTime.now().month - 1]} ${DateTime.now().day}, ${DateTime.now().year}';
      
      await ProfileStore.saveHistoryItem({
        'category': widget.category,
        'date': dateStr,
        'overall_score': reportData['overall_score'] ?? 78,
      });

      _analyzingTimer?.cancel();
      if (mounted) {
        setState(() {
          _analyzingProgress = 1.0;
          _finalReportData = reportData;
          _uiStatus = InterviewUIStatus.completed;
        });
      }
    } catch (e) {
      _analyzingTimer?.cancel();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to compile results: $e')),
        );
        Navigator.pop(context);
      }
    }
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    if (_uiStatus == InterviewUIStatus.analyzing) {
      return _buildAnalyzingScreen();
    } else if (_uiStatus == InterviewUIStatus.completed) {
      return _buildCompletedScreen();
    } else {
      return _buildInterviewWorkspace();
    }
  }

  // --- 1. INTERVIEW ACTIVE WORKSPACE (Screen 9, 11) ---
  Widget _buildInterviewWorkspace() {
    final size = MediaQuery.of(context).size;
    final currentQuestion = widget.questions.isNotEmpty 
        ? widget.questions[_currentQuestionIndex] 
        : 'Loading question...';

    return Scaffold(
      backgroundColor: const Color(0xFFF8F4EA),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D3A31).withOpacity(0.08),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      'Question ${_currentQuestionIndex + 1}/${widget.questions.length}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF0D3A31),
                        fontSize: 13,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.timer_outlined, color: Color(0xFFD8B28A), size: 16),
                        const SizedBox(width: 6),
                        Text(
                          _formatDuration(_secondsElapsed),
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            color: Color(0xFF0D3A31),
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),

              // Question Text Card
              Text(
                currentQuestion,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0D3A31),
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 20),

              // Listening Banner Indicator
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D3A31),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(color: Colors.greenAccent, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          _isVoiceRecordingActive ? 'Listening...' : 'Preparing...',
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Camera Feed Frame (Rounded Card)
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: _hudColor, width: 2),
                    boxShadow: [
                      BoxShadow(
                        color: _hudColor.withOpacity(0.04),
                        blurRadius: 15,
                        spreadRadius: 2,
                      )
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(22),
                    child: Stack(
                      children: [
                        if (_isCameraInitialized && _cameraController != null)
                          SizedBox.expand(
                            child: FittedBox(
                              fit: BoxFit.cover,
                              child: SizedBox(
                                width: _cameraController!.value.previewSize!.height,
                                height: _cameraController!.value.previewSize!.width,
                                child: CameraPreview(_cameraController!),
                              ),
                            ),
                          )
                        else
                          const Center(
                            child: CircularProgressIndicator(color: Color(0xFF0D3A31)),
                          ),

                        // Real-time AI Telemetry Overlay Card
                        if (_isCameraInitialized)
                          Positioned(
                            top: 16,
                            right: 16,
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(16),
                              child: BackdropFilter(
                                filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.85),
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(color: Colors.white.withOpacity(0.2), width: 1.5),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withOpacity(0.04),
                                        blurRadius: 10,
                                        spreadRadius: 1,
                                      )
                                    ],
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      _buildLiveIndicatorItem(
                                        icon: Icons.emoji_emotions_rounded,
                                        label: 'Mood Tracker',
                                        value: _emotion[0].toUpperCase() + _emotion.substring(1),
                                        color: const Color(0xFF0D3A31),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),

                        // Alert notification overlay
                        if (_currentAlert != null)
                          Positioned(
                            bottom: 16,
                            left: 16,
                            right: 16,
                            child: SlideTransition(
                              position: Tween<Offset>(
                                begin: const Offset(0, 0.5),
                                end: Offset.zero,
                              ).animate(CurvedAnimation(
                                parent: _alertController,
                                curve: Curves.easeOutBack,
                              )),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.95),
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: _hudColor, width: 1),
                                ),
                                child: Row(
                                  children: [
                                    Icon(Icons.warning_amber_rounded, color: _hudColor, size: 20),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        _currentAlert!,
                                        style: const TextStyle(
                                          color: Color(0xFF0D3A31),
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Bottom sound wave and button controls
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Audio Waveform
                  SizedBox(
                    height: 48,
                    width: double.infinity,
                    child: AnimatedBuilder(
                      animation: _waveformController,
                      builder: (context, child) {
                        return CustomPaint(
                          painter: WaveformPainter(
                            amplitude: _waveformAmplitude,
                            phase: _waveformController.value * 2 * math.pi,
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 18),

                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _isSpeakingModeActive ? const Color(0xFFD8B28A) : const Color(0xFF0D3A31).withOpacity(0.08),
                      foregroundColor: _isSpeakingModeActive ? Colors.white : const Color(0xFF0D3A31),
                      minimumSize: const Size(double.infinity, 56),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(28),
                        side: _isSpeakingModeActive ? BorderSide.none : const BorderSide(color: Color(0xFF0D3A31), width: 1.5),
                      ),
                      elevation: 0,
                    ),
                    icon: Icon(
                      _isSpeakingModeActive ? Icons.mic_rounded : Icons.mic_none_rounded,
                      color: _isSpeakingModeActive ? Colors.white : const Color(0xFF0D3A31),
                    ),
                    onPressed: () async {
                      if (_isSpeakingModeActive) return; // Already recording
                      await _flutterTts?.stop();
                      _cancelTtsBackupTimer();
                      setState(() {
                        _isSpeakingModeActive = true;
                      });
                      await _startRecordingForQuestion();
                    },
                    label: Text(
                      _isSpeakingModeActive ? 'RECORDING ANSWER...' : 'TAP TO START SPEAKING',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: _isSpeakingModeActive ? Colors.white : const Color(0xFF0D3A31),
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0D3A31),
                            foregroundColor: Colors.white,
                            minimumSize: const Size(double.infinity, 58),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(29),
                            ),
                            elevation: 0,
                          ),
                          onPressed: () {
                            if (_currentQuestionIndex < widget.questions.length - 1) {
                              _triggerChunkUploadAndNext();
                            } else {
                              _endInterview();
                            }
                          },
                          child: Text(
                            _currentQuestionIndex < widget.questions.length - 1 
                                ? 'NEXT QUESTION' 
                                : 'FINISH & SCORE',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, letterSpacing: 1),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- 2. AI ANALYZING SCREEN (Screen 10) ---
  Widget _buildAnalyzingScreen() {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F4EA),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              // Animated Robot / brain avatar loader
              Container(
                width: 150,
                height: 150,
                decoration: BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                  border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08), width: 2),
                ),
                child: Center(
                  child: Container(
                    width: 120,
                    height: 120,
                    decoration: const BoxDecoration(
                      color: Color(0xFFFAF7F0),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.insights_rounded,
                      size: 64,
                      color: Color(0xFF0D3A31),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 36),
              const Text(
                'AI Analyzing...',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 28,
                  color: Color(0xFF0D3A31),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Please wait while we evaluate your response metrics',
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xFF5A6561), fontSize: 14),
              ),
              const SizedBox(height: 32),

              // Progress Indicator Bar
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _analyzingProgress,
                  minHeight: 8,
                  backgroundColor: const Color(0xFFEADBC8).withOpacity(0.4),
                  valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF0D3A31)),
                ),
              ),
              const SizedBox(height: 48),

              // Mock feedback metrics loader
              _buildProgressMetricRow('Speech Clarity', (_analyzingProgress * 88).round()),
              const SizedBox(height: 12),
              _buildProgressMetricRow('Confidence', (_analyzingProgress * 84).round()),
              const SizedBox(height: 12),
              _buildProgressMetricRow('Eye Contact', (_analyzingProgress * 90).round()),
              const SizedBox(height: 12),
              _buildProgressMetricRow('Posture Alignment', (_analyzingProgress * 80).round()),

              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProgressMetricRow(String metric, int value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          metric,
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Color(0xFF0D3A31)),
        ),
        Text(
          '$value%',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF0D3A31)),
        ),
      ],
    );
  }

  // --- 3. INTERVIEW COMPLETED SCREEN (Screen 12) ---
  Widget _buildCompletedScreen() {
    final overallScore = _finalReportData?['overall_score'] ?? 78;
    return Scaffold(
      backgroundColor: const Color(0xFFF8F4EA),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              // Checkmark Circle
              Container(
                width: 120,
                height: 120,
                decoration: const BoxDecoration(
                  color: Color(0xFF0D3A31),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check_rounded,
                  size: 64,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 36),
              const Text(
                'Interview Completed!',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 28,
                  color: Color(0xFF0D3A31),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "Great job! We've analyzed your performance.",
                style: TextStyle(color: Color(0xFF5A6561), fontSize: 15),
              ),
              Text(
                'Overall Score: $overallScore%',
                style: const TextStyle(color: Color(0xFF0D3A31), fontWeight: FontWeight.bold, fontSize: 18),
              ),
              const Spacer(),

              // View Results Button (Forest Green)
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0D3A31),
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 58),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(29),
                  ),
                  elevation: 0,
                ),
                onPressed: () {
                  Navigator.pushReplacementNamed(
                    context,
                    '/report',
                    arguments: {
                      'sessionId': widget.sessionId,
                      'category': widget.category,
                      'preFetchedReport': _finalReportData,
                    },
                  );
                },
                child: const Text(
                  'View Results',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
              const SizedBox(height: 14),

              // Go to Dashboard Button (Sand / Gold outline)
              OutlinedButton(
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 58),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(29),
                  ),
                  side: const BorderSide(color: Color(0xFF0D3A31), width: 1.5),
                ),
                onPressed: () {
                  Navigator.pushReplacementNamed(context, '/home');
                },
                child: const Text(
                  'Go to Dashboard',
                  style: TextStyle(color: Color(0xFF0D3A31), fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
  Widget _buildLiveIndicatorItem({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w600,
                color: const Color(0xFF5A6561).withOpacity(0.8),
              ),
            ),
            Text(
              value,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// Custom Painter for the pulsing Face Alignment HUD Guide
class HudGuidePainter extends CustomPainter {
  final Color color;
  final double pulse;

  HudGuidePainter({required this.color, required this.pulse});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color.withOpacity(0.85)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    final outerPaint = Paint()
      ..color = color.withOpacity(0.2 - (pulse * 0.5).clamp(0, 0.2))
      ..strokeWidth = 1.0 + (pulse * 20)
      ..style = PaintingStyle.stroke;

    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final outerRect = Rect.fromLTWH(
      -pulse * 15,
      -pulse * 15,
      size.width + pulse * 30,
      size.height + pulse * 30,
    );

    // Corner brackets drawing
    canvas.drawArc(rect, math.pi, math.pi / 2, false, paint);
    canvas.drawArc(outerRect, math.pi, math.pi / 2, false, outerPaint);
    
    canvas.drawArc(rect, 1.5 * math.pi, math.pi / 2, false, paint);
    canvas.drawArc(outerRect, 1.5 * math.pi, math.pi / 2, false, outerPaint);

    canvas.drawArc(rect, 0.5 * math.pi, math.pi / 2, false, paint);
    canvas.drawArc(outerRect, 0.5 * math.pi, math.pi / 2, false, outerPaint);

    canvas.drawArc(rect, 0, math.pi / 2, false, paint);
    canvas.drawArc(outerRect, 0, math.pi / 2, false, outerPaint);

    final centerPaint = Paint()
      ..color = color.withOpacity(0.5)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), 3, centerPaint);
  }

  @override
  bool shouldRepaint(covariant HudGuidePainter oldDelegate) {
    return oldDelegate.color != color || oldDelegate.pulse != pulse;
  }
}

// Custom Painter for the responsive sine audio wave
class WaveformPainter extends CustomPainter {
  final double amplitude;
  final double phase;

  WaveformPainter({required this.amplitude, required this.phase});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke;

    final width = size.width;
    final height = size.height;
    final midY = height / 2;

    final waves = [
      {'amp': amplitude * 20.0, 'freq': 0.02, 'color': const Color(0xFF0D3A31).withOpacity(0.2), 'shift': 0.0},
      {'amp': amplitude * 12.0, 'freq': 0.035, 'color': const Color(0xFFD8B28A).withOpacity(0.8), 'shift': math.pi / 2},
      {'amp': amplitude * 6.0, 'freq': 0.05, 'color': const Color(0xFF0D3A31).withOpacity(0.6), 'shift': math.pi},
    ];

    for (var w in waves) {
      paint.color = w['color'] as Color;
      final path = Path();
      
      for (double x = 0; x <= width; x += 3) {
        final envelope = math.sin((x / width) * math.pi);
        final y = midY + (w['amp'] as double) * envelope * math.sin(x * (w['freq'] as double) + phase + (w['shift'] as double));
        
        if (x == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant WaveformPainter oldDelegate) {
    return oldDelegate.amplitude != amplitude || oldDelegate.phase != phase;
  }
}
