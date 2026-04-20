import 'package:flutter/material.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../services/enrollment_service.dart';
import '../services/background_service.dart';
import '../services/fcm_service.dart';
import 'status_screen.dart';

class EnrollmentScreen extends StatefulWidget {
  const EnrollmentScreen({super.key});

  @override
  State<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends State<EnrollmentScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _empIdCtrl = TextEditingController();
  final _deptCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _enroll() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });

    final pushToken = await FCMService.getToken();

    final result = await EnrollmentService.enrollDevice(
      employeeName: _nameCtrl.text.trim(),
      employeeEmail: _emailCtrl.text.trim(),
      employeeId: _empIdCtrl.text.trim(),
      department: _deptCtrl.text.trim(),
      pushToken: pushToken ?? '',
    );

    if (!mounted) return;
    setState(() => _loading = false);

    if (result.success) {
      await FCMService.initialize();
      await BackgroundService.startForegroundService();
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const StatusScreen()),
      );
    } else {
      setState(() => _error = result.error ?? 'Enrollment failed');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1565C0),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              elevation: 8,
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.security, size: 64, color: Color(0xFF1565C0)),
                      const SizedBox(height: 12),
                      const Text('Company Device Enrollment',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      const Text(
                        'This device will be enrolled in the company MDM system. '
                        'Security policies will be applied to protect company data.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey, fontSize: 13),
                      ),
                      const SizedBox(height: 24),
                      _field(_nameCtrl, 'Full Name', Icons.person),
                      const SizedBox(height: 12),
                      _field(_emailCtrl, 'Work Email', Icons.email,
                          keyboard: TextInputType.emailAddress),
                      const SizedBox(height: 12),
                      _field(_empIdCtrl, 'Employee ID', Icons.badge),
                      const SizedBox(height: 12),
                      _field(_deptCtrl, 'Department', Icons.business),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(_error!, style: const TextStyle(color: Colors.red)),
                      ],
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF1565C0),
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: _loading ? null : _enroll,
                          child: _loading
                              ? const CircularProgressIndicator(color: Colors.white)
                              : const Text('Enroll Device',
                                  style: TextStyle(fontSize: 16)),
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'By enrolling, you acknowledge this device will be monitored '
                        'per company policy.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(TextEditingController ctrl, String label, IconData icon,
      {TextInputType? keyboard}) {
    return TextFormField(
      controller: ctrl,
      keyboardType: keyboard,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
      ),
      validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
    );
  }
}
