
import 'package:flutter/material.dart';

class DotoriButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;
  final bool loading;
  const DotoriButton({super.key, required this.text, required this.onPressed, this.loading=false});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: loading ? null : onPressed,
        child: loading ? const SizedBox(width:16,height:16,child:CircularProgressIndicator(strokeWidth:2)) : Text(text),
      ),
    );
  }
}
