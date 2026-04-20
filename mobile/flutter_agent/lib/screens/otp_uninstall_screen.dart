import 'package:flutter/material.dart';
import '../services/command_executor.dart';

/// Shown when admin sends a remote uninstall command.
/// Employee must enter admin-provided OTP to proceed.
class OTPUninstallScreen extends StatefulWidget {
  final String commandId;
  final String otpId;

  const OTPUninstallScreen({
    super.key,
    required this.commandId,
    required this.otpId,
  });

  @override
  State<OTPUninstallScreen> createState() => _OTPUninstallScreenState();
}

class _OTPUninstallScreenState extends State<OTPUninstallScreen> {
  final _otpCtrl = TextEditingController();
  bool _loading = false;
  String? _error;
  int _attemptsLeft = 3;

  Future<void> _verify() async {
    final code = _otpCtrl.text.trim();
    if (code.length != 6) {
      setState(() => _error = 'Please enter the 6-digit passcode');
      return;
    }

    setState(() { _loading = true; _error = null; });

    try {
      await CommandExecutor.executeVerifiedUninstall(
        widget.commandId,
        widget.otpId,
        code,
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      setState(() {
        _loading = false;
        _attemptsLeft--;
        _error = _attemptsLeft > 0
            ? 'Incorrect passcode. $_attemptsLeft attempt(s) remaining.'
            : 'Maximum attempts exceeded. Contact IT support.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.admin_panel_settings, size: 48, color: Color(0xFF1565C0)),
            const SizedBox(height: 12),
            const Text(
              'Admin Authorization Required',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            const Text(
              'Your IT administrator has initiated device uninstall. '
              'Enter the authorization passcode provided by your IT admin to proceed.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey, fontSize: 13),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _otpCtrl,
              keyboardType: TextInputType.number,
              maxLength: 6,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 24, letterSpacing: 8),
              decoration: InputDecoration(
                hintText: '------',
                counterText: '',
                labelText: 'Authorization Passcode',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
            ],
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _loading ? null : () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: (_loading || _attemptsLeft <= 0) ? null : _verify,
                    child: _loading
                        ? const SizedBox(
                            width: 20, height: 20,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2))
                        : const Text('Authorize'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
