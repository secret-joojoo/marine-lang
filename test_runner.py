import os
import sys
import io
import glob
from interpreter import MarineLangInterpreter, MarineError

def run_all_tests(test_dir="tests"):
    if not os.path.exists(test_dir):
        print(f"흥! '{test_dir}' 폴더가 없잖아! 바보 아니야? 빨리 만들기나 해!")
        return

    test_files = glob.glob(os.path.join(test_dir, "*.ak"))
    if not test_files:
        print(f"새끼... 기열! '{test_dir}' 폴더에 .ak 파일이 하나도 없잖아! 당장 작성해!")
        return

    passed = 0
    failed = 0

    print("===" * 15)
    print("오도기합짜세 해병 테스트")
    print("===" * 15)

    for ak_file in sorted(test_files):
        base_name = os.path.splitext(ak_file)[0]
        out_file = base_name + ".out"
        in_file = base_name + ".in"

        if not os.path.exists(out_file):
            print(f"⚠️ [경고] {os.path.basename(out_file)} 파일이 없어! 테스트를 건너뛴다! 기열!")
            continue

        with open(out_file, 'r', encoding='utf-8') as f:
            expected_output = f.read().strip()

        user_input = ""
        if os.path.exists(in_file):
            with open(in_file, 'r', encoding='utf-8') as f:
                user_input = f.read()

        with open(ak_file, 'r', encoding='utf-8') as f:
            code = f.read()

        old_stdout = sys.stdout
        old_stdin = sys.stdin
        sys.stdout = captured_stdout = io.StringIO()
        sys.stdin = io.StringIO(user_input)
        
        try:
            interpreter = MarineLangInterpreter(code)
            interpreter.run()
            actual_output = captured_stdout.getvalue().strip()
        except MarineError as e:
            actual_output = str(e).strip()
        except Exception as e:
            actual_output = f"알 수 없는 오류: {e}"
        finally:
            sys.stdout = old_stdout
            sys.stdin = old_stdin

        if actual_output == expected_output:
            print(f"✅ {os.path.basename(ak_file)}: 기합!")
            passed += 1
        else:
            print(f"❌ {os.path.basename(ak_file)}: 기열!")
            print(f"   [예상 결과]:\n     > {expected_output}")
            print(f"   [실제 결과]:\n     > {actual_output}")
            failed += 1

    print("===" * 15)
    print(f"최종 결과: {passed} 기합, {failed} 찐빠")
    print("===" * 15)

if __name__ == "__main__":
    run_all_tests()