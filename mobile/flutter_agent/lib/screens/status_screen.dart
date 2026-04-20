import 'package:flutter/material.dart';
import '../services/command_executor.dart';
import 'otp_uninstall_screen.dart';

class StatusScreen extends StatefulWidget {
  const StatusScreen({super.key});

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  @override
  void initState() {
    super.initState();
    // Listen for remote uninstall commands
    CommandExecutor.onUninstallRequest.listen((data) {
      if (mounted) {
        _showUninstallDialog(data['command_id']!, data['otp_id']!);
      }
    });
  }

  void _showUninstallDialog(String commandId, String otpId) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => OTPUninstallScreen(
        commandId: commandId,
        otpId: otpId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Device Security'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            _StatusCard(
              icon: Icons.verified_user,
              title: 'Device Enrolled',
              subtitle: 'This device is managed by company policy',
              color: Colors.green,
            ),
            const SizedBox(height: 16),
            _StatusCard(
              icon: Icons.lock,
              title: 'Uninstall Protection Active',
              subtitle: 'Admin authorization required to remove this app',
              color: const Color(0xFF1565C0),
            ),
            const SizedBox(height: 16),
            _StatusCard(
              icon: Icons.location_on,
              title: 'Location Monitoring',
              subtitle: 'Company location tracking is active per policy',
              color: Colors.orange,
            ),
            const SizedBox(height: 16),
            _StatusCard(
              icon: Icons.apps,
              title: 'App Usage Reporting',
              subtitle: 'App usage is reported to IT per company policy',
              color: Colors.purple,
            ),
            const Spacer(),
            const Text(
              'This is a company-managed device. All monitoring activities '
              'are disclosed per your employment agreement.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;

  const _StatusCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.15),
          child: Icon(icon, color: color),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
      ),
    );
  }
}
