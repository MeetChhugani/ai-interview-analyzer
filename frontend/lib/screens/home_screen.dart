import 'dart:ui';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/profile_store.dart';
import '../services/auth_store.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  int _currentTab = 0; // 0: Home, 1: History, 2: Analytics, 3: Profile

  Map<String, dynamic>? _userProfile;
  List<Map<String, dynamic>> _historyReports = [];

  final List<Map<String, dynamic>> _commonQuestions = [
    {
      'question': 'Tell me about yourself and your background.',
      'tag': 'Introduction',
      'icon': Icons.person_pin_rounded,
      'color': const Color(0xFF8B5CF6), // Purple
    },
    {
      'question': 'What are your key strengths and weaknesses?',
      'tag': 'Self-Assessment',
      'icon': Icons.insights_rounded,
      'color': const Color(0xFFF59E0B), // Amber
    },
    {
      'question': 'Why do you want to join our company and why should we hire you?',
      'tag': 'Motivation',
      'icon': Icons.work_outline_rounded,
      'color': const Color(0xFFEC4899), // Pink
    },
    {
      'question': 'How do you handle pressure, tight deadlines, or challenging scenarios?',
      'tag': 'Behavioral',
      'icon': Icons.track_changes_rounded,
      'color': const Color(0xFF10B981), // Emerald
    },
  ];

  @override
  void initState() {
    super.initState();
    _loadProfileAndHistory();
  }

  Future<void> _loadProfileAndHistory() async {
    final profile = await ProfileStore.loadProfile();
    final user = await AuthStore.getAuthUser();
    
    List<Map<String, dynamic>> history = [];
    if (user != null && user['id'] != null) {
      try {
        history = await _apiService.getHistoryFromServer(user['id']);
      } catch (e) {
        print('Error loading history from server: $e');
        history = await ProfileStore.loadHistory();
      }
    } else {
      history = await ProfileStore.loadHistory();
    }

    if (mounted) {
      setState(() {
        _userProfile = profile;
        _historyReports = history;
      });
    }
  }

  Future<void> _startInterview(String category, {int questionCount = 5}) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final user = await AuthStore.getAuthUser();
      final userId = user?['id'];
      
      final sessionData = await _apiService.createSession(category, userId: userId, questionCount: questionCount);
      final sessionId = sessionData['session_id'];

      if (mounted) {
        Navigator.pushNamed(
          context,
          '/interview',
          arguments: {
            'sessionId': sessionId,
            'category': category,
            'questions': List<String>.from(sessionData['questions'] ?? []),
          },
        ).then((_) => _loadProfileAndHistory()); // Reload history upon return
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error initializing session: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _showInterviewSetupBottomSheet(String defaultCategory) {
    String selectedCategory = defaultCategory;
    double selectedCount = 5.0; // Default to 5 questions

    final dropdownItems = [
      'Software Engineer',
      'Software Developer',
      'Product Manager',
      'Data Analyst',
      'HR Manager',
      'Android Developer',
      'Investment Banker',
      'Sales Representative',
      'Marketing Specialist',
      'Nurse',
      'Doctor',
      'Research Scientist',
      'Customer Support Specialist',
      'Project Manager',
      'Teacher / Educator',
      'Hotel Manager',
      'Chartered Accountant',
      'Graphic Designer',
      'Cybersecurity Analyst',
      'Mechanical Engineer',
      'Business Analyst',
    ];

    if (!dropdownItems.contains(selectedCategory)) {
      dropdownItems.add(selectedCategory);
    }

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(30),
          topRight: Radius.circular(30),
        ),
      ),
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 24.0,
                right: 24.0,
                top: 24.0,
                bottom: MediaQuery.of(context).viewInsets.bottom + 32.0,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: Container(
                      width: 48,
                      height: 5,
                      decoration: BoxDecoration(
                        color: const Color(0xFF0D3A31).withOpacity(0.12),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  const Row(
                    children: [
                      Icon(Icons.tune_rounded, color: Color(0xFF0D3A31), size: 24),
                      SizedBox(width: 12),
                      Text(
                        'Interview Settings',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF0D3A31),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Customize your practice session before launching the AI coach.',
                    style: TextStyle(
                      color: const Color(0xFF5A6561).withOpacity(0.9),
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Job Category / Field',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: Color(0xFF0D3A31),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFAF7F0),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: selectedCategory,
                        dropdownColor: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF0D3A31)),
                        style: const TextStyle(
                          color: Color(0xFF0D3A31),
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                        isExpanded: true,
                        items: dropdownItems.map((role) {
                          return DropdownMenuItem<String>(
                            value: role,
                            child: Text(role),
                          );
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setModalState(() => selectedCategory = val);
                          }
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Number of Questions',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                          color: Color(0xFF0D3A31),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0D3A31).withOpacity(0.08),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          '${selectedCount.toInt()} Qs',
                          style: const TextStyle(
                            color: Color(0xFF0D3A31),
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      activeTrackColor: const Color(0xFF0D3A31),
                      inactiveTrackColor: const Color(0xFF0D3A31).withOpacity(0.08),
                      thumbColor: const Color(0xFF0D3A31),
                      overlayColor: const Color(0xFF0D3A31).withOpacity(0.12),
                      valueIndicatorColor: const Color(0xFF0D3A31),
                      valueIndicatorTextStyle: const TextStyle(color: Colors.white),
                    ),
                    child: Slider(
                      value: selectedCount,
                      min: 1.0,
                      max: 20.0,
                      divisions: 19,
                      label: selectedCount.toInt().toString(),
                      onChanged: (val) {
                        setModalState(() => selectedCount = val);
                      },
                    ),
                  ),
                  const SizedBox(height: 32),
                  ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      _startInterview(selectedCategory, questionCount: selectedCount.toInt());
                    },
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      backgroundColor: const Color(0xFF0D3A31),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                      elevation: 0,
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.play_arrow_rounded, color: Colors.white),
                        SizedBox(width: 8),
                        Text(
                          'START AI SESSION',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                            letterSpacing: 1.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _startCustomQuestionInterview(String question, String tag) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final sessionData = await _apiService.createSession(
        'General Practice', 
        customQuestions: [question],
      );
      final sessionId = sessionData['session_id'];

      if (mounted) {
        Navigator.pushNamed(
          context,
          '/interview',
          arguments: {
            'sessionId': sessionId,
            'category': 'General Practice ($tag)',
            'questions': List<String>.from(sessionData['questions'] ?? []),
          },
        ).then((_) => _loadProfileAndHistory());
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error initializing session: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _showCustomQuestionsDialog() {
    final textController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) {
        return BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: AlertDialog(
            backgroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(24),
              side: const BorderSide(color: Color(0xFFFAF7F0), width: 1),
            ),
            title: const Row(
              children: [
                Icon(Icons.edit_note_rounded, color: Color(0xFF0D3A31), size: 28),
                SizedBox(width: 10),
                Text(
                  'Custom Interview',
                  style: TextStyle(color: Color(0xFF0D3A31), fontWeight: FontWeight.bold),
                ),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Type or paste your custom interview questions below (one question per line).',
                  style: TextStyle(color: Color(0xFF5A6561), fontSize: 13, height: 1.4),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: textController,
                  maxLines: 5,
                  style: const TextStyle(color: Color(0xFF0D3A31), fontSize: 14),
                  decoration: InputDecoration(
                    labelText: 'Questions List',
                    labelStyle: const TextStyle(color: Color(0xFF0D3A31)),
                    hintText: 'e.g.\nWhat is your experience with Flutter?\nTell me about a challenging bug you resolved.',
                    hintStyle: TextStyle(color: const Color(0xFF0D3A31).withOpacity(0.3)),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: const Color(0xFF0D3A31).withOpacity(0.12)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: Color(0xFF0D3A31)),
                    ),
                    filled: true,
                    fillColor: const Color(0xFFF8F4EA).withOpacity(0.5),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel', style: TextStyle(color: Color(0xFF5A6561))),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0D3A31),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  final text = textController.text.trim();
                  if (text.isNotEmpty) {
                    final questions = text
                        .split('\n')
                        .map((q) => q.trim())
                        .where((q) => q.isNotEmpty)
                        .toList();
                    if (questions.isNotEmpty) {
                      Navigator.pop(context);
                      _startCustomQuestionsSession(questions);
                    }
                  }
                },
                child: const Text('Start Practice', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _startCustomQuestionsSession(List<String> questions) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final user = await AuthStore.getAuthUser();
      final userId = user?['id'];
      
      final sessionData = await _apiService.createSession(
        'Custom Practice', 
        customQuestions: questions,
        userId: userId,
      );
      final sessionId = sessionData['session_id'];

      if (mounted) {
        Navigator.pushNamed(
          context,
          '/interview',
          arguments: {
            'sessionId': sessionId,
            'category': 'Custom Practice',
            'questions': List<String>.from(sessionData['questions'] ?? []),
          },
        ).then((_) => _loadProfileAndHistory());
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error initializing session: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _showSettingsDialog() {
    final textController = TextEditingController(text: ApiService.serverIp);
    showDialog(
      context: context,
      builder: (context) {
        return BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: AlertDialog(
            backgroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(24),
              side: const BorderSide(color: Color(0xFFEADBC8), width: 1),
            ),
            title: const Row(
              children: [
                Icon(Icons.dns_rounded, color: Color(0xFF0D3A31)),
                SizedBox(width: 10),
                Text(
                  'Server Configuration',
                  style: TextStyle(color: Color(0xFF0D3A31), fontWeight: FontWeight.bold),
                ),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Set the backend IP and port. Use 127.0.0.1:8000 for USB reverse mapping, or your PC\'s local IP (e.g., 192.168.1.15:8000).',
                  style: TextStyle(color: Color(0xFF5A6561), fontSize: 13, height: 1.4),
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: textController,
                  style: const TextStyle(color: Color(0xFF0D3A31), fontFamily: 'monospace'),
                  decoration: InputDecoration(
                    labelText: 'Backend Address',
                    labelStyle: const TextStyle(color: Color(0xFF0D3A31)),
                    hintText: '127.0.0.1:8000',
                    hintStyle: TextStyle(color: const Color(0xFF0D3A31).withOpacity(0.3)),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: const Color(0xFF0D3A31).withOpacity(0.12)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: Color(0xFF0D3A31)),
                    ),
                    filled: true,
                    fillColor: const Color(0xFFF8F4EA).withOpacity(0.5),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel', style: TextStyle(color: Color(0xFF5A6561))),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0D3A31),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  setState(() {
                    ApiService.serverIp = textController.text.trim();
                  });
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Server updated to: ${ApiService.serverIp}'),
                      backgroundColor: const Color(0xFF10B981),
                    ),
                  );
                },
                child: const Text('Save Settings', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final name = _userProfile?['name'] ?? 'Arjun';

    return Scaffold(
      backgroundColor: const Color(0xFFF8F4EA),
      body: Stack(
        children: [
          SafeArea(
            child: Column(
              children: [
                // Header Area
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0D3A31),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(
                          Icons.psychology_rounded,
                          size: 24,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text(
                        'INTERVIEW.AI',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                          letterSpacing: 1.5,
                          color: Color(0xFF0D3A31),
                        ),
                      ),
                      const Spacer(),
                      IconButton(
                        icon: const Icon(Icons.settings_rounded, color: Color(0xFF0D3A31)),
                        onPressed: _showSettingsDialog,
                        tooltip: 'Server Settings',
                      ),
                    ],
                  ),
                ),

                // Tab Content
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: _buildTabContent(name),
                  ),
                ),
              ],
            ),
          ),

          // Loading Overlay
          if (_isLoading)
            _buildLoadingOverlay(),
        ],
      ),
      bottomNavigationBar: _buildBottomNavigationBar(),
    );
  }

  Widget _buildTabContent(String userName) {
    switch (_currentTab) {
      case 0:
        return _buildHomeTab(userName);
      case 1:
        return _buildHistoryTab();
      case 2:
        return _buildAnalyticsTab();
      case 3:
        return _buildProfileTab();
      default:
        return const SizedBox();
    }
  }

  // --- HOME TAB (Screen 3) ---
  Widget _buildHomeTab(String userName) {
    final role = _userProfile?['currentRole'] ?? 'Software Developer';
    return CustomScrollView(
      physics: const BouncingScrollPhysics(),
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Hello, $userName 👋',
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 28,
                    color: Color(0xFF0D3A31),
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Ready to ace your interview?',
                  style: TextStyle(
                    color: Color(0xFF5A6561),
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 24),

                // Main Banner Button (Start New Interview)
                GestureDetector(
                  onTap: () => _showInterviewSetupBottomSheet(role),
                  child: Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D3A31),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF0D3A31).withOpacity(0.12),
                          blurRadius: 15,
                          offset: const Offset(0, 5),
                        )
                      ],
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Start New Interview',
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 20,
                                  color: Colors.white,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'AI will ask questions based on your profile & resume',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.65),
                                  fontSize: 13,
                                  height: 1.3,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: const BoxDecoration(
                            color: Color(0xFFFAF7F0), // Cream circle
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.arrow_forward_rounded,
                            color: Color(0xFF0D3A31),
                            size: 24,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // Practice Modes title
                const Text(
                  'Practice Modes',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                    color: Color(0xFF0D3A31),
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),

        // Practice Mode cards list
        SliverPadding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          sliver: SliverList(
            delegate: SliverChildListDelegate([
              _buildPracticeModeCard(
                title: 'Mock Interview',
                subtitle: 'Full interview simulation',
                icon: Icons.assignment_outlined,
                onTap: () => _showInterviewSetupBottomSheet(role),
              ),
              const SizedBox(height: 12),
              _buildPracticeModeCard(
                title: 'Quick Practice',
                subtitle: 'Practice with standard questions',
                icon: Icons.timer_outlined,
                onTap: () => setState(() => _currentTab = 1), // Link to Quick Prep or list below
              ),
              const SizedBox(height: 12),
              _buildPracticeModeCard(
                title: 'Custom Interview',
                subtitle: 'Practice your own questions',
                icon: Icons.edit_note_outlined,
                onTap: _showCustomQuestionsDialog,
              ),
              const SizedBox(height: 32),
              
              // Common Prep list header
              const Text(
                'Quick Practice (Common Questions)',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF0D3A31),
                ),
              ),
              const SizedBox(height: 12),
            ]),
          ),
        ),

        // Quick Prep questions list
        SliverPadding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          sliver: SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) {
                final q = _commonQuestions[index];
                return _buildCommonQuestionItem(q);
              },
              childCount: _commonQuestions.length,
            ),
          ),
        ),

        const SliverToBoxAdapter(
          child: SizedBox(height: 40),
        ),
      ],
    );
  }

  Widget _buildPracticeModeCard({required String title, required String subtitle, required IconData icon, required VoidCallback onTap}) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18.0, vertical: 16.0),
            child: Row(
              children: [
                Icon(icon, color: const Color(0xFF0D3A31), size: 24),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF0D3A31)),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: TextStyle(fontSize: 12, color: const Color(0xFF5A6561).withOpacity(0.8)),
                      ),
                    ],
                  ),
                ),
                Icon(Icons.arrow_forward_ios_rounded, color: const Color(0xFF0D3A31).withOpacity(0.3), size: 14),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCommonQuestionItem(Map<String, dynamic> q) {
    final color = q['color'] as Color;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.18)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _startCustomQuestionInterview(q['question'] as String, q['tag'] as String),
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 16.0),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    q['icon'] as IconData,
                    color: color,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: color.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          q['tag'] as String,
                          style: TextStyle(
                            color: color,
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        q['question'] as String,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 13.5,
                          color: Color(0xFF0D3A31),
                          height: 1.3,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  color: const Color(0xFF0D3A31).withOpacity(0.2),
                  size: 14,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // --- HISTORY TAB ---
  Widget _buildHistoryTab() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          const Text(
            'Interview History',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 24, color: Color(0xFF0D3A31)),
          ),
          const SizedBox(height: 6),
          Text(
            'Your completed mock sessions.',
            style: TextStyle(color: const Color(0xFF5A6561).withOpacity(0.9), fontSize: 14),
          ),
          const SizedBox(height: 20),
          Expanded(
            child: _historyReports.isEmpty
                ? _buildEmptyState('No interview sessions recorded yet.', Icons.history_edu_rounded)
                : ListView.builder(
                    physics: const BouncingScrollPhysics(),
                    itemCount: _historyReports.length,
                    itemBuilder: (context, index) {
                      final item = _historyReports[index];
                      final score = item['overall_score'] ?? 0;
                      final date = item['date'] ?? 'Just now';
                      final category = item['category'] ?? 'General Prep';
                      
                      return Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: const Color(0xFF0D3A31).withOpacity(0.1),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(Icons.assignment_outlined, color: Color(0xFF0D3A31), size: 22),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    category,
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF0D3A31)),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    date,
                                    style: TextStyle(fontSize: 12, color: const Color(0xFF5A6561).withOpacity(0.6)),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                              decoration: BoxDecoration(
                                color: const Color(0xFF0D3A31).withOpacity(0.08),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                '$score%',
                                style: const TextStyle(
                                  color: Color(0xFF0D3A31),
                                  fontWeight: FontWeight.bold,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  // --- ANALYTICS TAB ---
  Widget _buildAnalyticsTab() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          const Text(
            'Analytics & Trends',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 24, color: Color(0xFF0D3A31)),
          ),
          const SizedBox(height: 6),
          Text(
            'Keep practicing to improve your delivery.',
            style: TextStyle(color: const Color(0xFF5A6561).withOpacity(0.9), fontSize: 14),
          ),
          const SizedBox(height: 24),
          Expanded(
            child: _historyReports.isEmpty
                ? _buildEmptyState('Complete an interview to view analytics.', Icons.bar_chart_rounded)
                : ListView(
                    physics: const BouncingScrollPhysics(),
                    children: [
                      _buildAnalyticsCard(
                        title: 'Overall Performance',
                        value: '${(_historyReports.map((e) => (e['overall_score'] as int)).reduce((a, b) => a + b) / _historyReports.length).round()}%',
                        subtitle: 'Average Interview Score',
                        color: const Color(0xFF0D3A31),
                      ),
                      const SizedBox(height: 16),
                      _buildAnalyticsCard(
                        title: 'Completed Practice Runs',
                        value: '${_historyReports.length}',
                        subtitle: 'Mock Sessions Completed',
                        color: const Color(0xFFD8B28A),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalyticsCard({required String title, required String value, required String subtitle, required Color color}) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: const Color(0xFF5A6561).withOpacity(0.8))),
          const SizedBox(height: 16),
          Row(
            children: [
              Text(
                value,
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 36, color: color),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  subtitle,
                  style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13, color: Color(0xFF0D3A31)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- PROFILE TAB ---
  Widget _buildProfileTab() {
    if (_userProfile == null) return const SizedBox();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 16),
          const Text(
            'User Profile',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 24, color: Color(0xFF0D3A31)),
          ),
          const SizedBox(height: 24),
          Expanded(
            child: ListView(
              physics: const BouncingScrollPhysics(),
              children: [
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
                  ),
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 40,
                        backgroundColor: const Color(0xFFFAF7F0),
                        child: const Icon(Icons.person, size: 48, color: Color(0xFF0D3A31)),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _userProfile!['name'] ?? 'Candidate',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: Color(0xFF0D3A31)),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _userProfile!['currentRole'] ?? 'Software Developer',
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Color(0xFF5A6561)),
                      ),
                      const Divider(height: 36, thickness: 0.8),
                      _buildProfileItem('Education', _userProfile!['education']),
                      _buildProfileItem('Experience', _userProfile!['experience']),
                      _buildProfileItem('Skills', (_userProfile!['skills'] as List<dynamic>).join(', ')),
                      _buildProfileItem('Resume', _userProfile!['resumeName']),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFBA1A1A),
                    foregroundColor: Colors.white,
                    minimumSize: const Size(double.infinity, 54),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(27)),
                    elevation: 0,
                  ),
                  onPressed: () async {
                    await AuthStore.clearAuthUser();
                    await ProfileStore.clearProfile();
                    await ProfileStore.clearHistory();
                    if (mounted) {
                      Navigator.pushReplacementNamed(context, '/login');
                    }
                  },
                  child: const Text('Log Out Account', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProfileItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: const Color(0xFF5A6561).withOpacity(0.8)),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF0D3A31)),
            ),
          ),
        ],
      ),
    );
  }

  // --- HELPERS ---
  Widget _buildEmptyState(String message, IconData icon) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 56, color: const Color(0xFF0D3A31).withOpacity(0.2)),
          const SizedBox(height: 12),
          Text(
            message,
            style: TextStyle(color: const Color(0xFF5A6561).withOpacity(0.5), fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomNavigationBar() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: const Color(0xFF0D3A31).withOpacity(0.06), width: 1)),
      ),
      child: BottomNavigationBar(
        currentIndex: _currentTab,
        onTap: (index) {
          setState(() {
            _currentTab = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: Colors.white,
        selectedItemColor: const Color(0xFF0D3A31),
        unselectedItemColor: const Color(0xFF5A6561).withOpacity(0.5),
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 11),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home_rounded),
            activeIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.assignment_outlined),
            activeIcon: Icon(Icons.assignment_rounded),
            label: 'History',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.bar_chart_rounded),
            activeIcon: Icon(Icons.bar_chart_rounded),
            label: 'Analytics',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline_rounded),
            activeIcon: Icon(Icons.person_rounded),
            label: 'Profile',
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingOverlay() {
    return Container(
      color: Colors.black.withOpacity(0.65),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFFEADBC8)),
              ),
              child: const CircularProgressIndicator(
                strokeWidth: 3,
                color: Color(0xFF0D3A31),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Initializing AI Session...',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 18,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Configuring video streams & speech engines',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
