import 'package:flutter/material.dart';

class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.park, size: 80),
                const SizedBox(height: 12),
                Text('도토리',
                    style: theme.displaySmall?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 40),
                SizedBox(
                  width: 280,
                  child: FilledButton(
                    onPressed: () => Navigator.pushNamed(context, '/login'),
                    child: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text('로그인하기'),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: 280,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pushNamed(context, '/register'),
                    child: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text('회원가입하기'),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                const Opacity(opacity: 0.6, child: Text('간편로그인은 곧 지원됩니다')),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
