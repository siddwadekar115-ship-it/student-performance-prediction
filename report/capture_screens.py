"""Save the demo website screens used in Chapter V."""

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

OUT = Path(__file__).resolve().parent / "figures"
BASE = "http://127.0.0.1:8081"


def shot(driver, name: str) -> None:
    path = OUT / name
    driver.save_screenshot(str(path))
    print(path, path.stat().st_size)


def login(driver, username: str, password: str) -> None:
    driver.get(BASE + "/logout")
    driver.get(BASE + "/")
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button").click()
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "header")))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,860")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--hide-scrollbars")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(BASE + "/logout")
        driver.get(BASE + "/")
        shot(driver, "screen_login.png")

        login(driver, "student", "student123")
        shot(driver, "screen_dashboard.png")

        driver.get(BASE + "/predict")
        for element in driver.find_elements(By.TAG_NAME, "select"):
            Select(element).select_by_index(1)
        driver.find_element(By.CSS_SELECTOR, "form button").click()
        heading = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h2"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'start'});", heading)
        driver.execute_script("window.scrollBy(0, -80);")
        shot(driver, "screen_predict.png")

        driver.get(BASE + "/exam")
        shot(driver, "screen_exam.png")
        seen = set()
        for radio in driver.find_elements(By.CSS_SELECTOR, "input[type=radio]"):
            name = radio.get_attribute("name")
            if name not in seen:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", radio)
                radio.click()
                seen.add(name)
        driver.find_element(By.CSS_SELECTOR, "form button").click()
        WebDriverWait(driver, 20).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), "My exam result")
        )
        shot(driver, "screen_my_result.png")

        login(driver, "teacher", "teacher123")
        driver.get(BASE + "/questions")
        shot(driver, "screen_questions.png")

        driver.get(BASE + "/internals")
        driver.find_element(By.NAME, "student_name").send_keys("Demo Student")
        driver.find_element(By.NAME, "subject").send_keys("Project")
        driver.find_element(By.NAME, "internal_marks").send_keys("24")
        driver.find_element(By.NAME, "assignment_score").send_keys("16")
        driver.find_element(By.NAME, "attendance_percent").send_keys("80")
        driver.find_element(By.CSS_SELECTOR, "form button").click()
        WebDriverWait(driver, 20).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Demo Student"))
        shot(driver, "screen_internals.png")

        driver.get(BASE + "/evaluation")
        shot(driver, "screen_evaluation.png")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
