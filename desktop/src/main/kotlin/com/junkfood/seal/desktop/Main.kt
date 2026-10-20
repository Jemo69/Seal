package com.junkfood.seal.desktop

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application

fun main() = application {
    Window(onCloseRequest = ::exitApplication, title = "Seal Desktop") {
        MaterialTheme {
            Text("Seal - Windows Port Pending")
        }
    }
}
