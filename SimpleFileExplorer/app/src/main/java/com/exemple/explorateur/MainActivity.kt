package com.exemple.explorateur

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.view.View
import android.webkit.MimeTypeMap
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File
import java.text.DecimalFormat

class MainActivity : AppCompatActivity() {

    private lateinit var listView: ListView
    private lateinit var pathLabel: TextView
    private lateinit var emptyLabel: TextView

    private val racine: File = Environment.getExternalStorageDirectory()
    private var courant: File = racine
    private var entrees: List<File> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        listView = findViewById(R.id.listView)
        pathLabel = findViewById(R.id.pathLabel)
        emptyLabel = findViewById(R.id.emptyLabel)

        listView.setOnItemClickListener { _, _, position, _ ->
            val cible = entrees[position]
            if (cible.isDirectory) {
                ouvrirDossier(cible)
            } else {
                ouvrirFichier(cible)
            }
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                val parent = courant.parentFile
                if (parent != null && courant.absolutePath != racine.absolutePath) {
                    ouvrirDossier(parent)
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })

        demanderPermission()
    }

    private fun demanderPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                AlertDialog.Builder(this)
                    .setTitle(R.string.permission_titre)
                    .setMessage(R.string.permission_message)
                    .setPositiveButton(R.string.ouvrir_reglages) { _, _ ->
                        val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                        intent.data = Uri.parse("package:$packageName")
                        startActivity(intent)
                    }
                    .setNegativeButton(android.R.string.cancel, null)
                    .show()
            } else {
                ouvrirDossier(courant)
            }
        } else {
            val permission = Manifest.permission.READ_EXTERNAL_STORAGE
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, arrayOf(permission), 1)
            } else {
                ouvrirDossier(courant)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && Environment.isExternalStorageManager()) {
            ouvrirDossier(courant)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            ouvrirDossier(courant)
        } else {
            Toast.makeText(this, R.string.permission_refusee, Toast.LENGTH_LONG).show()
        }
    }

    private fun ouvrirDossier(dossier: File) {
        courant = dossier
        pathLabel.text = dossier.absolutePath

        val tousFichiers = dossier.listFiles()?.toList() ?: emptyList()
        entrees = tousFichiers.sortedWith(
            compareByDescending<File> { it.isDirectory }.thenBy { it.name.lowercase() }
        )

        if (entrees.isEmpty()) {
            emptyLabel.visibility = View.VISIBLE
            listView.visibility = View.GONE
        } else {
            emptyLabel.visibility = View.GONE
            listView.visibility = View.VISIBLE
        }

        val libelles = entrees.map { afficherEntree(it) }
        listView.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, libelles)
    }

    private fun afficherEntree(fichier: File): String {
        return if (fichier.isDirectory) {
            "[D]  ${fichier.name}"
        } else {
            "      ${fichier.name}   (${tailleLisible(fichier.length())})"
        }
    }

    private fun tailleLisible(octets: Long): String {
        if (octets < 1024) return "$octets o"
        val unites = arrayOf("Kio", "Mio", "Gio", "Tio")
        var valeur = octets.toDouble() / 1024
        var i = 0
        while (valeur >= 1024 && i < unites.size - 1) {
            valeur /= 1024
            i++
        }
        return "${DecimalFormat("0.#").format(valeur)} ${unites[i]}"
    }

    private fun ouvrirFichier(fichier: File) {
        try {
            val uri: Uri = FileProvider.getUriForFile(
                this,
                "$packageName.fileprovider",
                fichier
            )
            val mime = MimeTypeMap.getSingleton()
                .getMimeTypeFromExtension(fichier.extension.lowercase())
                ?: "*/*"
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, mime)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(Intent.createChooser(intent, getString(R.string.ouvrir_avec)))
        } catch (e: Exception) {
            Toast.makeText(this, getString(R.string.erreur_ouverture, e.message), Toast.LENGTH_LONG).show()
        }
    }
}
