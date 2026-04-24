import os
import sys
import io
import glob
from interpreter import MarineLangInterpreter, MarineError

def run_tests(test_dir="tests"):
    print("===" * 15)
    print("기합 해병 테스트!!")
    print("===" * 15)

    total_passed = 0
    total_failed = 0
    modules = [d for d in os.listdir(test_dir) if os.path.isdir(os.path.join(test_dir, d))]
    module_result = {}

    for module in modules:
        dir = os.path.join(test_dir, module)
        test_files = glob.glob(os.path.join(dir, "*.ak"))

        print(f"\n[{module.upper()} 테스트 실시!!]")

        passed = 0
        failed = 0

        for ak_file in test_files:
            base_name = os.path.splitext(ak_file)[0]
            out_file = base_name + ".out"
            in_file = base_name + ".in"

            with open(ak_file, 'r', encoding='utf-8') as f:
                code = f.read()

            with open(out_file, 'r', encoding='utf-8') as f:
                expected_output = f.read().strip()
            
            user_input = ""
            if os.path.exists(in_file):
                with open(in_file, 'r', encoding='utf-8') as f:
                    user_input = f.read()

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
                passed += 1
            else:
                print(f"❌ {os.path.basename(ak_file)}: 기열!")
                print(f"   [예상 결과]:\n     > {expected_output}")
                print(f"   [실제 결과]:\n     > {actual_output}")
                failed += 1

        module_result[module] = (passed, failed)
        total_passed += passed
        total_failed += failed
        if failed == 0:
            print(f"✅ {module.upper()} 기합!")
    
    print("\n" + "===" * 15)
    print("기합 해병 테스트 결과 보고")
    print("===" * 15)

    for module, (passed, failed) in module_result.items():
        print(f"{module.upper()}\t\t기합: {passed}개,\t기열: {failed}개")

    print("===" * 15)
    print(f"최종 결과\t기합: {total_passed}개,\t기열: {total_failed}개")
    print("===" * 15)


if __name__ == "__main__":
    run_tests()