function orderSuccess() {

    // Play celebration sound
    let audio = new Audio("/static/sounds/success.mp3");
    audio.play();

    // Speak after a short delay
    setTimeout(function () {
        let msg = new SpeechSynthesisUtterance(
            "Your order has been placed successfully. Thank you for choosing RP Biryaani."
        );
        msg.lang = "en-IN";
        speechSynthesis.speak(msg);
    }, 1000);
}