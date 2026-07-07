import 'package:flutter/material.dart';
import '../services/profile_store.dart';
import '../services/auth_store.dart';
import '../services/api_service.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _currentStep = 0; // 0: Splash, 1: Greeting, 2: Setup 1, 3: Setup 2, 4: Setup 3 (Resume), 5: Setup 4 (Details), 6: Summary

  // Profile data controllers
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  
  String _education = 'B.Tech - Computer Science';
  String _experience = '2 Years';
  String _currentRole = 'Software Engineer';
  final TextEditingController _customRoleController = TextEditingController();
  
  bool _isResumeUploaded = false;
  String _resumeFileName = '';
  
  String _expLevel = 'Mid Level (2-5 years)';
  String _interviewType = 'Technical';
  List<String> _selectedSkills = ['Flutter', 'Dart', 'Firebase'];
  String _prefLanguage = 'English';

  final List<String> _availableSkills = ['Flutter', 'Dart', 'Firebase', 'Python', 'SQL', 'Git', 'HTML/CSS', 'Machine Learning'];

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _customRoleController.dispose();
    super.dispose();
  }

  void _nextStep() {
    if (_currentStep == 1) {
      if (_nameController.text.trim().isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please enter your name')),
        );
        return;
      }
    }
    setState(() {
      _currentStep++;
    });
  }

  void _prevStep() {
    setState(() {
      if (_currentStep > 0) _currentStep--;
    });
  }

  Future<void> _finishOnboarding() async {
    final finalRole = _currentRole == 'Custom / Other...' 
        ? (_customRoleController.text.trim().isNotEmpty ? _customRoleController.text.trim() : 'Custom Role')
        : _currentRole;

    final profile = {
      'name': _nameController.text.trim(),
      'email': _emailController.text.trim(),
      'phone': _phoneController.text.trim(),
      'education': _education,
      'experience': _experience,
      'currentRole': finalRole,
      'resumeName': _isResumeUploaded ? _resumeFileName : 'No resume uploaded',
      'expLevel': _expLevel,
      'interviewType': _interviewType,
      'skills': _selectedSkills,
      'language': _prefLanguage,
    };
    await ProfileStore.saveProfile(profile);

    // Sync with backend database
    try {
      final authUser = await AuthStore.getAuthUser();
      if (authUser != null && authUser['id'] != null) {
        final apiService = ApiService();
        await apiService.updateProfile(authUser['id'], profile);
        
        // Update cached auth user values locally
        authUser['education'] = _education;
        authUser['experience'] = _experience;
        authUser['current_role'] = finalRole;
        authUser['skills'] = _selectedSkills;
        await AuthStore.saveAuthUser(authUser);
      }
    } catch (e) {
      print('Failed to sync profile with server: $e');
    }

    if (mounted) {
      Navigator.pushReplacementNamed(context, '/home');
    }
  }

  @override
  Widget build(BuildContext context) {
    // Return corresponding screen based on _currentStep
    if (_currentStep == 0) {
      return _buildSplashScreen();
    } else if (_currentStep == 1) {
      return _buildGreetingScreen();
    } else {
      return Scaffold(
        backgroundColor: const Color(0xFFF8F4EA),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_currentStep >= 2 && _currentStep <= 5) _buildProgressIndicator(),
                const SizedBox(height: 24),
                Expanded(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    child: _buildStepContent(),
                  ),
                ),
                const SizedBox(height: 16),
                _buildNavigationButtons(),
              ],
            ),
          ),
        ),
      );
    }
  }

  // --- 1. SPLASH SCREEN (Screen 1) ---
  Widget _buildSplashScreen() {
    return Scaffold(
      backgroundColor: const Color(0xFF0D3A31), // Deep green
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              // Logo placeholder icon
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFFD8B28A).withOpacity(0.5), width: 1.5),
                ),
                child: const Icon(
                  Icons.psychology_rounded,
                  size: 56,
                  color: Color(0xFFD8B28A), // Warm gold
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'AI Smart\nInterview Analyzer',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  fontSize: 32,
                  height: 1.25,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Real-time AI analysis to\nimprove your interview skills',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 16,
                  height: 1.4,
                ),
              ),
              const Spacer(),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFAF7F0), // Warm gold/cream
                  foregroundColor: const Color(0xFF0D3A31),
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(28),
                  ),
                  elevation: 0,
                ),
                onPressed: _nextStep,
                child: const Text(
                  'Get Started',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
              const SizedBox(height: 24),
              // Dots indicator mockup
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(4, (i) {
                  return Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == 0 ? 16 : 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: i == 0 ? const Color(0xFFD8B28A) : Colors.white24,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  );
                }),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- 2. GREETING SCREEN (Screen 2) ---
  Widget _buildGreetingScreen() {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F4EA),
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 20),
              const Text(
                'Hi there! 👋',
                style: TextStyle(
                  color: Color(0xFF0D3A31),
                  fontWeight: FontWeight.w800,
                  fontSize: 32,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "What's your name?",
                style: TextStyle(
                  color: Color(0xFF0D3A31),
                  fontWeight: FontWeight.bold,
                  fontSize: 24,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "Let's begin with a quick introduction.",
                style: TextStyle(
                  color: Color(0xFF5A6561),
                  fontSize: 15,
                ),
              ),
              const SizedBox(height: 30),
              TextField(
                controller: _nameController,
                style: const TextStyle(color: Color(0xFF0D3A31), fontSize: 16),
                decoration: InputDecoration(
                  hintText: 'Enter your name',
                  hintStyle: TextStyle(color: const Color(0xFF0D3A31).withOpacity(0.4)),
                  filled: true,
                  fillColor: Colors.white,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide(color: const Color(0xFF0D3A31).withOpacity(0.12)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: const BorderSide(color: Color(0xFF0D3A31), width: 1.5),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0D3A31),
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(28),
                  ),
                  elevation: 0,
                ),
                onPressed: _nextStep,
                child: const Text(
                  'Continue',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
              const SizedBox(height: 30),
              // Robot image mockup
              Center(
                child: Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFAF7F0),
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFFEADBC8)),
                  ),
                  child: const Icon(
                    Icons.android_rounded, // fallback robot icon
                    size: 70,
                    color: Color(0xFF0D3A31),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- PROFILE BUILDER STEPS ---

  Widget _buildProgressIndicator() {
    int activeStep = _currentStep - 1; // Step 1 to 4
    double progress = activeStep / 4.0;
    String title = '';
    if (_currentStep == 2) title = 'Complete Your Profile';
    if (_currentStep == 3) title = 'Tell us about yourself';
    if (_currentStep == 4) title = 'Upload Your Resume';
    if (_currentStep == 5) title = 'More about you';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: Color(0xFF0D3A31),
                fontWeight: FontWeight.w800,
                fontSize: 22,
              ),
            ),
            Text(
              'Step $activeStep of 4',
              style: const TextStyle(
                color: Color(0xFF5A6561),
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // Linear Progress Bar
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: const Color(0xFFEADBC8).withOpacity(0.5),
            valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF0D3A31)),
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _buildStepContent() {
    switch (_currentStep) {
      case 2: // Setup 1: Personal Details (Screen 4)
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'This helps AI personalize your interview experience.',
              style: TextStyle(color: Color(0xFF5A6561), fontSize: 14),
            ),
            const SizedBox(height: 28),
            _buildFieldLabel('Full Name'),
            _buildTextField(_nameController, 'Your Full Name'),
            const SizedBox(height: 20),
            _buildFieldLabel('Email'),
            _buildTextField(_emailController, 'yourname@example.com', keyboardType: TextInputType.emailAddress),
            const SizedBox(height: 20),
            _buildFieldLabel('Phone Number'),
            _buildTextField(_phoneController, '+91 98765 43210', keyboardType: TextInputType.phone),
          ],
        );
      case 3: // Setup 2: Professional (Screen 5)
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildFieldLabel('Highest Education'),
            _buildDropdownField(
              value: _education,
              items: [
                'B.Tech - Computer Science',
                'M.Tech - Computer Science',
                'MBA - Marketing',
                'B.Sc - Information Technology',
                'MCA',
                'Bachelor of Arts'
              ],
              onChanged: (val) => setState(() => _education = val!),
            ),
            const SizedBox(height: 20),
            _buildFieldLabel('Work Experience'),
            _buildDropdownField(
              value: _experience,
              items: ['Freshman', '1 Year', '2 Years', '3 Years', '5+ Years'],
              onChanged: (val) => setState(() => _experience = val!),
            ),
            const SizedBox(height: 20),
            _buildFieldLabel('Current Role'),
            _buildDropdownField(
              value: _currentRole,
              items: [
                'Software Engineer',
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
                'Custom / Other...'
              ],
              onChanged: (val) => setState(() => _currentRole = val!),
            ),
            if (_currentRole == 'Custom / Other...') ...[
              const SizedBox(height: 16),
              _buildFieldLabel('Enter Custom Job Title'),
              _buildTextField(_customRoleController, 'e.g. Mechanical Engineer, Pilot, Chef'),
            ],
          ],
        );
      case 4: // Setup 3: Resume (Screen 6)
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 10),
            GestureDetector(
              onTap: () {
                setState(() {
                  _isResumeUploaded = true;
                  _resumeFileName = '${_nameController.text.trim().replaceAll(' ', '_')}_Resume.pdf';
                });
              },
              child: Container(
                height: 180,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: const Color(0xFF0D3A31).withOpacity(0.12),
                    style: BorderStyle.solid,
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.cloud_upload_outlined,
                      size: 48,
                      color: Color(0xFF0D3A31),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Drag & drop your file here',
                      style: TextStyle(color: Color(0xFF0D3A31), fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'or Browse File',
                      style: TextStyle(color: const Color(0xFF0D3A31).withOpacity(0.5), fontSize: 13),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            if (_isResumeUploaded) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.picture_as_pdf_rounded, color: Colors.redAccent, size: 36),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _resumeFileName,
                            style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0D3A31), fontSize: 14),
                          ),
                          const SizedBox(height: 4),
                          Text('248 KB', style: TextStyle(color: const Color(0xFF0D3A31).withOpacity(0.4), fontSize: 12)),
                        ],
                      ),
                    ),
                    const Icon(Icons.check_circle, color: Colors.green, size: 24),
                  ],
                ),
              ),
            ],
          ],
        );
      case 5: // Setup 4: Details (Screen 7)
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildFieldLabel('Experience Level'),
            _buildDropdownField(
              value: _expLevel,
              items: ['Entry Level (0-2 years)', 'Mid Level (2-5 years)', 'Senior Level (5+ years)'],
              onChanged: (val) => setState(() => _expLevel = val!),
            ),
            const SizedBox(height: 20),
            _buildFieldLabel('Interview Type'),
            _buildDropdownField(
              value: _interviewType,
              items: ['Technical', 'Behavioral', 'Managerial', 'General HR'],
              onChanged: (val) => setState(() => _interviewType = val!),
            ),
            const SizedBox(height: 20),
            _buildFieldLabel('Key Skills (Optional)'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _availableSkills.map((skill) {
                final isSelected = _selectedSkills.contains(skill);
                return FilterChip(
                  label: Text(skill),
                  selected: isSelected,
                  selectedColor: const Color(0xFF0D3A31).withOpacity(0.12),
                  checkmarkColor: const Color(0xFF0D3A31),
                  labelStyle: TextStyle(
                    color: isSelected ? const Color(0xFF0D3A31) : const Color(0xFF5A6561),
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    fontSize: 13,
                  ),
                  backgroundColor: Colors.white,
                  side: BorderSide(
                    color: isSelected ? const Color(0xFF0D3A31) : const Color(0xFF0D3A31).withOpacity(0.12),
                    width: 1,
                  ),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                  onSelected: (selected) {
                    setState(() {
                      if (selected) {
                        _selectedSkills.add(skill);
                      } else {
                        _selectedSkills.remove(skill);
                      }
                    });
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 20),
            _buildFieldLabel('Preferred Interview Language'),
            _buildDropdownField(
              value: _prefLanguage,
              items: ['English', 'Spanish', 'Hindi', 'German'],
              onChanged: (val) => setState(() => _prefLanguage = val!),
            ),
          ],
        );
      case 6: // Profile Summary (Screen 8)
        return _buildProfileSummaryScreen();
      default:
        return const SizedBox();
    }
  }

  // --- Step 6: PROFILE SUMMARY SCREEN (Screen 8) ---
  Widget _buildProfileSummaryScreen() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 10),
        const Text(
          'Profile Summary',
          style: TextStyle(
            color: Color(0xFF0D3A31),
            fontWeight: FontWeight.w800,
            fontSize: 26,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Review your information.',
          style: TextStyle(color: Color(0xFF5A6561), fontSize: 14),
        ),
        const SizedBox(height: 28),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0D3A31).withOpacity(0.03),
                blurRadius: 20,
                spreadRadius: 2,
              )
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 36,
                    backgroundColor: const Color(0xFFFAF7F0),
                    child: const Icon(Icons.person, size: 40, color: Color(0xFF0D3A31)),
                  ),
                  const SizedBox(width: 18),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _nameController.text.trim(),
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: Color(0xFF0D3A31)),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _currentRole,
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Color(0xFF5A6561)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(height: 36, thickness: 0.8),
              _buildSummaryItem(Icons.work_history_outlined, 'Experience', _experience),
              const SizedBox(height: 14),
              _buildSummaryItem(Icons.school_outlined, 'Education', _education),
              const SizedBox(height: 14),
              _buildSummaryItem(
                Icons.insights_rounded,
                'Key Skills',
                _selectedSkills.isEmpty ? 'None selected' : _selectedSkills.join(', '),
              ),
              const SizedBox(height: 14),
              _buildSummaryItem(
                Icons.picture_as_pdf_outlined,
                'Resume',
                _isResumeUploaded ? _resumeFileName : 'No file',
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryItem(IconData icon, String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: const Color(0xFF0D3A31).withOpacity(0.65)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(fontSize: 12, color: const Color(0xFF5A6561).withOpacity(0.8), fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF0D3A31)),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // --- BUTTON NAVIGATION BAR ---
  Widget _buildNavigationButtons() {
    if (_currentStep == 6) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12.0),
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
          onPressed: _finishOnboarding,
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Start Interview',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(width: 8),
              Icon(Icons.rocket_launch, size: 20),
            ],
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
        children: [
          if (_currentStep > 2) ...[
            Expanded(
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(28),
                  ),
                  side: BorderSide(color: const Color(0xFF0D3A31).withOpacity(0.2)),
                ),
                onPressed: _prevStep,
                child: const Text(
                  'Back',
                  style: TextStyle(color: Color(0xFF0D3A31), fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ),
            ),
            const SizedBox(width: 16),
          ],
          Expanded(
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0D3A31),
                foregroundColor: Colors.white,
                minimumSize: const Size(double.infinity, 56),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(28),
                ),
                elevation: 0,
              ),
              onPressed: _currentStep == 5 ? _nextStep : _nextStep,
              child: Text(
                _currentStep == 5 ? 'Finish' : 'Next',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- REUSABLE FIELD BUILDERS ---
  Widget _buildFieldLabel(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0, left: 4.0),
      child: Text(
        label,
        style: const TextStyle(
          color: Color(0xFF0D3A31),
          fontWeight: FontWeight.bold,
          fontSize: 14,
        ),
      ),
    );
  }

  Widget _buildTextField(TextEditingController controller, String hint, {TextInputType keyboardType = TextInputType.text}) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      style: const TextStyle(color: Color(0xFF0D3A31), fontSize: 15),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: const Color(0xFF0D3A31).withOpacity(0.35)),
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: const Color(0xFF0D3A31).withOpacity(0.08)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF0D3A31), width: 1.5),
        ),
      ),
    );
  }

  Widget _buildDropdownField({required String value, required List<String> items, required ValueChanged<String?> onChanged}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF0D3A31).withOpacity(0.08)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          icon: const Icon(Icons.keyboard_arrow_down_rounded, color: Color(0xFF0D3A31)),
          dropdownColor: Colors.white,
          borderRadius: BorderRadius.circular(14),
          style: const TextStyle(color: Color(0xFF0D3A31), fontSize: 15, fontWeight: FontWeight.w500),
          items: items.map((item) {
            return DropdownMenuItem<String>(
              value: item,
              child: Text(item),
            );
          }).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }
}
