function loadVideo(videoId) {
    const videoHtml = `
        <iframe width="560" height="315"
            src="${videoId}"
            title="YouTube video player"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowfullscreen>
        </iframe>
    `;
    document.getElementById("video-container").innerHTML = videoHtml;
}
loadVideo("0VO0kOj0Qfg");