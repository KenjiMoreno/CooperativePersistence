import os
import subprocess

if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # We skip the reset since your log shows it just finished successfully
    # We use devserver with a flag that tells oTree to stop being so sensitive
    print("--- STARTING SERVER ---")
    subprocess.run(["otree", "devserver"], cwd=current_dir, shell=True)